"""Configuration loading for narrate."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


NARRATE_HOME = Path.home() / ".narrate"
DEFAULT_VOICES_DIR = NARRATE_HOME / "voices"


@dataclass
class NarrateConfig:
    voices_dir: Path = field(default_factory=lambda: DEFAULT_VOICES_DIR)
    default_voice: str | None = None
    output_format: str = "wav"
    turn_gap: float = 0.4
    engine: str = "chatterbox"
    device: str = "auto"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_map: dict[str, str] = field(default_factory=dict)


def load_config(path: Path | None = None) -> NarrateConfig:
    """Load config from narrate.toml. Checks cwd first, then ~/.narrate/."""
    if path is None:
        local = Path("narrate.toml")
        global_ = NARRATE_HOME / "narrate.toml"
        if local.exists():
            path = local
        elif global_.exists():
            path = global_
        else:
            return NarrateConfig()

    if not path.exists():
        return NarrateConfig()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    kwargs: dict = {}

    voices = data.get("voices", {})
    if "dir" in voices:
        kwargs["voices_dir"] = Path(voices["dir"])
    if "default" in voices:
        kwargs["default_voice"] = voices["default"]

    output = data.get("output", {})
    if "format" in output:
        kwargs["output_format"] = output["format"]
    if "turn_gap" in output:
        kwargs["turn_gap"] = output["turn_gap"]

    engine = data.get("engine", {})
    if "default" in engine:
        kwargs["engine"] = engine["default"]
    if "device" in engine:
        kwargs["device"] = engine["device"]

    el = data.get("elevenlabs", {})
    if "api_key" in el:
        kwargs["elevenlabs_api_key"] = el["api_key"]
    if "voice_map" in el:
        kwargs["elevenlabs_voice_map"] = dict(el["voice_map"])

    # Environment variable overrides config file for API key
    env_key = os.environ.get("ELEVENLABS_API_KEY")
    if env_key:
        kwargs["elevenlabs_api_key"] = env_key

    return NarrateConfig(**kwargs)
