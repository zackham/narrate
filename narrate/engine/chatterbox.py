"""Chatterbox Turbo TTS engine adapter."""

from __future__ import annotations

import logging
import os
import sys
import warnings
from contextlib import contextmanager
from pathlib import Path

# Suppress noisy upstream library warnings before any chatterbox imports
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*Reference mel length.*")
for _logger_name in ("chatterbox", "chatterbox.tts_turbo", "huggingface_hub"):
    logging.getLogger(_logger_name).setLevel(logging.ERROR)
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

# Perth watermarker fallback — must run before importing chatterbox.
# The native PerthImplicitWatermarker fails on some platforms, causing
# ChatterboxTurboTTS.from_pretrained() to crash with "NoneType not callable"
try:
    import perth
    if perth.PerthImplicitWatermarker is None:
        perth.PerthImplicitWatermarker = perth.DummyWatermarker
except ImportError:
    pass

import click
import numpy as np
import soundfile as sf

from narrate.engine import TTSEngine


@contextmanager
def _suppress_upstream_output():
    """Suppress stdout/stderr noise from upstream libraries (tqdm bars, print statements)."""
    devnull = open(os.devnull, "w")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = devnull, devnull
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        devnull.close()

# Minimum voice clip duration Chatterbox needs for good results
MIN_VOICE_DURATION = 5.0


class ChatterboxEngine(TTSEngine):
    """Local TTS via Chatterbox Turbo (350M params)."""

    needs_wav = True

    def __init__(self, device: str = "auto") -> None:
        self._device_spec = device
        self._model = None
        self._current_voice: Path | None = None

    def _resolve_device(self) -> str:
        import torch

        if self._device_spec == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if self._device_spec == "cuda" and not torch.cuda.is_available():
            raise click.ClickException(
                "CUDA device requested but no GPU available "
                "— use --device cpu or --device auto"
            )
        return self._device_spec

    def _load_model(self) -> None:
        device = self._resolve_device()
        from chatterbox.tts_turbo import ChatterboxTurboTTS

        try:
            with _suppress_upstream_output():
                self._model = ChatterboxTurboTTS.from_pretrained(device=device)
        except Exception as e:
            raise click.ClickException(
                f"Failed to load Chatterbox model: {e}. "
                "Run `narrate --help` for troubleshooting."
            )

    @staticmethod
    def _check_voice_duration(voice_ref: Path) -> None:
        """Validate that the voice clip is at least MIN_VOICE_DURATION seconds."""
        try:
            info = sf.info(str(voice_ref))
            duration = info.duration
        except Exception:
            return  # If we can't read it, let Chatterbox surface its own error
        if duration < MIN_VOICE_DURATION:
            raise click.ClickException(
                f"voice clip '{voice_ref.name}' is {duration:.1f}s "
                f"— must be at least {MIN_VOICE_DURATION:.0f} seconds"
            )

    def prepare_voice(self, voice_ref: Path) -> None:
        if self._model is None:
            self._load_model()
        if self._current_voice != voice_ref:
            self._check_voice_duration(voice_ref)
            with _suppress_upstream_output():
                self._model.prepare_conditionals(
                    str(voice_ref), norm_loudness=True
                )
            self._current_voice = voice_ref

    def generate(self, text: str, voice_ref: Path) -> tuple[int, np.ndarray]:
        if self._model is None:
            self._load_model()
        self.prepare_voice(voice_ref)
        with _suppress_upstream_output():
            wav = self._model.generate(text)
        return (self._model.sr, wav.cpu().numpy().squeeze())
