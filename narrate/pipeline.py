"""Audio pipeline: chunk, generate, stitch, normalize, output."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import click
import numpy as np
import soundfile as sf

from narrate.engine import TTSEngine
from narrate.parser import Turn
from narrate.voices import resolve_voice


def chunk_text(text: str, max_chars: int = 280) -> list[str]:
    """Split text at sentence boundaries, merging short sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        elif current:
            current = current + " " + sentence
        else:
            current = sentence

    if current:
        # Handle single sentence exceeding max_chars
        while len(current) > max_chars:
            split_at = current[:max_chars].rfind(" ")
            if split_at <= 0:
                split_at = max_chars
            chunks.append(current[:split_at])
            current = current[split_at:].lstrip()
        if current:
            chunks.append(current)

    return chunks if chunks else [text]


def generate_audio(
    turns: list[Turn],
    engine: TTSEngine,
    voices_dir: Path,
    turn_gap: float = 0.4,
    normalize: bool = True,
    progress_callback: Callable[[int], None] | None = None,
) -> tuple[int, np.ndarray]:
    """Run the full audio pipeline: chunk -> generate -> stitch -> normalize."""
    segments: list[np.ndarray] = []
    sample_rate: int | None = None

    for i, turn in enumerate(turns):
        text = turn.text.strip() if turn.text else ""

        # Pause/silence turns: explicit pause_seconds, empty text, ellipsis-only, or no voice
        # Insert clean silence instead of trying to synthesize
        pause_dur = getattr(turn, 'pause_seconds', None)
        if pause_dur or not text or text == "..." or not turn.voice:
            if sample_rate is not None:
                dur = float(pause_dur) if pause_dur else turn_gap
                pause_samples = int(sample_rate * dur)
                segments.append(np.zeros(pause_samples))
            if progress_callback is not None:
                progress_callback(1)
            continue

        # Only resolve to a WAV file when the engine needs one
        if engine.needs_wav:
            voice_ref: Path | str = resolve_voice(turn.voice, voices_dir)
        else:
            voice_ref = turn.voice

        chunks = chunk_text(text)

        turn_audio_parts: list[np.ndarray] = []
        for chunk in chunks:
            sr, audio = engine.generate(chunk, voice_ref)
            if sample_rate is None:
                sample_rate = sr
            turn_audio_parts.append(audio)
            if progress_callback is not None:
                progress_callback(1)

        # Concatenate chunks within a turn (no gap)
        if turn_audio_parts:
            turn_audio = np.concatenate(turn_audio_parts)
            segments.append(turn_audio)

        # Insert silence gap between turns
        if i < len(turns) - 1 and sample_rate is not None:
            gap_samples = int(sample_rate * turn_gap)
            segments.append(np.zeros(gap_samples))

    if not segments or sample_rate is None:
        raise click.ClickException("no audio generated — check your script")

    audio = np.concatenate(segments)

    if normalize:
        try:
            import warnings

            import pyloudnorm

            meter = pyloudnorm.Meter(sample_rate)
            loudness = meter.integrated_loudness(audio)
            if not np.isinf(loudness):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    audio = pyloudnorm.normalize.loudness(audio, loudness, -16.0)
        except Exception:
            pass  # Normalization is best-effort

    return (sample_rate, audio)


def _infer_format(path: Path, explicit_fmt: str | None) -> str:
    """Infer output format from file extension, warn on mismatch."""
    ext = path.suffix.lower().lstrip(".")
    supported = {"wav", "mp3"}

    if explicit_fmt:
        if ext in supported and ext != explicit_fmt:
            click.echo(
                f"Warning: output extension '.{ext}' does not match "
                f"--format {explicit_fmt}",
                err=True,
            )
        return explicit_fmt

    if ext in supported:
        return ext

    return "wav"


def write_output(
    sr: int,
    audio: np.ndarray,
    path: Path,
    fmt: str | None = None,
) -> None:
    """Write audio to file (WAV directly, MP3 via ffmpeg).

    If *fmt* is None the format is inferred from the file extension.
    """
    resolved_fmt = _infer_format(path, fmt)

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    if resolved_fmt == "wav":
        sf.write(str(path), audio, sr)
    elif resolved_fmt == "mp3":
        if not shutil.which("ffmpeg"):
            raise click.ClickException(
                "ffmpeg not found — install ffmpeg for MP3 output, "
                "or use --format wav"
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            sf.write(tmp_path, audio, sr)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, "-b:a", "192k", str(path)],
                check=True,
                capture_output=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        raise click.ClickException(f"unsupported format: {resolved_fmt}")
