"""TTS engine abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from narrate.config import NarrateConfig


class TTSEngine(ABC):
    """Base class for TTS engines."""

    needs_wav: bool = True
    """Whether this engine needs a local WAV file for voice references."""

    @abstractmethod
    def generate(self, text: str, voice_ref: Path | str) -> tuple[int, np.ndarray]:
        """Generate audio. Returns (sample_rate, audio_array)."""
        ...

    def prepare_voice(self, voice_ref: Path) -> None:
        """Pre-compute voice conditionals. Default no-op."""
        pass


def get_engine(name: str, config: NarrateConfig) -> TTSEngine:
    """Factory: create a TTS engine by name."""
    if name == "chatterbox":
        from narrate.engine.chatterbox import ChatterboxEngine
        return ChatterboxEngine(device=config.device)
    elif name == "elevenlabs":
        from narrate.engine.elevenlabs import ElevenLabsEngine
        return ElevenLabsEngine(
            api_key=config.elevenlabs_api_key,
            voice_map=config.elevenlabs_voice_map,
        )
    else:
        raise ValueError(f"unknown engine: {name!r} — choose 'chatterbox' or 'elevenlabs'")
