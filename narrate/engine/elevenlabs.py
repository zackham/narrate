"""ElevenLabs TTS engine adapter (cloud, requires API key)."""

from __future__ import annotations

import io
from pathlib import Path

import click
import httpx
import numpy as np
import soundfile as sf

from narrate.engine import TTSEngine

_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsEngine(TTSEngine):
    """Cloud TTS via ElevenLabs REST API."""

    needs_wav = False

    def __init__(self, api_key: str, voice_map: dict[str, str]) -> None:
        if not api_key:
            raise click.ClickException(
                "ElevenLabs engine requires an API key — set ELEVENLABS_API_KEY "
                "or add [elevenlabs] api_key to narrate.toml"
            )
        self._api_key = api_key
        self._voice_map = voice_map

    def generate(self, text: str, voice_ref: Path | str) -> tuple[int, np.ndarray]:
        # Accept either a Path (legacy) or a voice name string
        if isinstance(voice_ref, Path):
            voice_name = voice_ref.stem.lower()
        else:
            voice_name = voice_ref.lower()
        voice_id = self._voice_map.get(voice_name)
        if not voice_id:
            raise click.ClickException(
                f"no ElevenLabs voice ID configured for '{voice_name}' "
                "— add it to [elevenlabs.voice_map] in narrate.toml"
            )

        try:
            resp = httpx.post(
                f"{_API_BASE}/{voice_id}",
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                params={"output_format": "mp3_44100_128"},
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                msg = "ElevenLabs authentication failed — check your API key"
            elif status == 429:
                msg = "ElevenLabs rate limit exceeded — wait and retry, or check your plan quota"
            else:
                msg = f"ElevenLabs API error (HTTP {status}) — {exc.response.text[:200]}"
            raise click.ClickException(msg) from exc
        except httpx.HTTPError as exc:
            raise click.ClickException(
                f"ElevenLabs request failed: {exc} — check your internet connection"
            ) from exc

        audio, sr = sf.read(io.BytesIO(resp.content))
        return (sr, audio)
