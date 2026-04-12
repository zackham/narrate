"""Tests for narrate.config."""

from pathlib import Path

from narrate.config import DEFAULT_VOICES_DIR, NarrateConfig, load_config


def test_defaults():
    cfg = NarrateConfig()
    assert cfg.voices_dir == DEFAULT_VOICES_DIR
    assert cfg.default_voice is None
    assert cfg.output_format == "wav"
    assert cfg.turn_gap == 0.4
    assert cfg.engine == "chatterbox"
    assert cfg.device == "auto"
    assert cfg.elevenlabs_api_key == ""
    assert cfg.elevenlabs_voice_map == {}


def test_load_missing_file(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg == NarrateConfig()


def test_load_valid_toml(tmp_path):
    toml_file = tmp_path / "narrate.toml"
    toml_file.write_text(
        '[voices]\ndir = "/tmp/v"\ndefault = "zack"\n\n'
        "[output]\nformat = \"mp3\"\nturn_gap = 0.6\n\n"
        '[engine]\ndefault = "elevenlabs"\ndevice = "cuda"\n\n'
        '[elevenlabs]\napi_key = "sk-test"\n'
        'voice_map = { zack = "abc123", adrian = "def456" }\n'
    )
    cfg = load_config(toml_file)
    assert cfg.voices_dir == Path("/tmp/v")
    assert cfg.default_voice == "zack"
    assert cfg.output_format == "mp3"
    assert cfg.turn_gap == 0.6
    assert cfg.engine == "elevenlabs"
    assert cfg.device == "cuda"
    assert cfg.elevenlabs_api_key == "sk-test"
    assert cfg.elevenlabs_voice_map == {"zack": "abc123", "adrian": "def456"}


def test_load_partial_toml(tmp_path):
    toml_file = tmp_path / "narrate.toml"
    toml_file.write_text('[voices]\ndefault = "olivia"\n')
    cfg = load_config(toml_file)
    assert cfg.default_voice == "olivia"
    assert cfg.voices_dir == DEFAULT_VOICES_DIR  # default preserved
    assert cfg.engine == "chatterbox"  # default preserved


def test_env_var_overrides_config(tmp_path, monkeypatch):
    toml_file = tmp_path / "narrate.toml"
    toml_file.write_text('[elevenlabs]\napi_key = "from-file"\n')
    monkeypatch.setenv("ELEVENLABS_API_KEY", "from-env")
    cfg = load_config(toml_file)
    assert cfg.elevenlabs_api_key == "from-env"
