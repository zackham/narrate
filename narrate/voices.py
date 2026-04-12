"""Voice directory scanning, resolution, and download."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click
import httpx

PREMADE_VOICES = [
    "Abigail", "Adrian", "Alexander", "Alice", "Austin", "Axel",
    "Connor", "Cora", "Elena", "Eli", "Emily", "Everett",
    "Gabriel", "Gianna", "Henry", "Ian", "Jade", "Jeremiah",
    "Jordan", "Julian", "Layla", "Leonardo", "Michael", "Miles",
    "Olivia", "Ryan", "Taylor", "Thomas",
]

_VOICE_BASE_URL = (
    "https://raw.githubusercontent.com/devnen/"
    "Chatterbox-TTS-Server/main/voices"
)


def list_voices(voices_dir: Path) -> list[str]:
    """Return sorted list of available voice names (lowercase stems)."""
    if not voices_dir.exists():
        return []
    return sorted(p.stem.lower() for p in voices_dir.glob("*.wav"))


def resolve_voice(name: str, voices_dir: Path) -> Path:
    """Resolve a voice name to its WAV file path (case-insensitive)."""
    lookup = {p.stem.lower(): p for p in voices_dir.glob("*.wav")}
    key = name.lower()
    if key not in lookup:
        raise click.ClickException(
            f"no voice file found for '{name}' — expected {voices_dir / f'{name}.wav'}"
        )
    return lookup[key]


def install_voices(
    voices_dir: Path,
    progress_callback: Callable[[int], None] | None = None,
) -> None:
    """Download pre-made voices from devnen/Chatterbox-TTS-Server."""
    voices_dir.mkdir(parents=True, exist_ok=True)

    skipped = 0
    downloaded = 0

    for name in PREMADE_VOICES:
        dest = voices_dir / f"{name.lower()}.wav"
        if dest.exists():
            skipped += 1
            if progress_callback is not None:
                progress_callback(1)  # type: ignore[operator]
            continue

        url = f"{_VOICE_BASE_URL}/{name}.wav"
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
            downloaded += 1
        except httpx.HTTPError:
            click.echo(
                f"Warning: failed to download voice '{name}' "
                "— check your internet connection.",
                err=True,
            )
        if progress_callback is not None:
            progress_callback(1)  # type: ignore[operator]

    dl_label = "voice" if downloaded == 1 else "voices"
    sk_label = "voice" if skipped == 1 else "voices"
    click.echo(f"Downloaded {downloaded} {dl_label}, skipped {skipped} {sk_label} existing.")
