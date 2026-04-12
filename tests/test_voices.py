"""Tests for narrate.voices."""

import pytest

from narrate.voices import (
    PREMADE_VOICES,
    install_voices,
    list_voices,
    resolve_voice,
)


def test_list_voices_populated(tmp_path):
    (tmp_path / "alice.wav").touch()
    (tmp_path / "Bob.wav").touch()
    (tmp_path / "charlie.wav").touch()
    result = list_voices(tmp_path)
    assert result == ["alice", "bob", "charlie"]


def test_list_voices_empty(tmp_path):
    result = list_voices(tmp_path)
    assert result == []


def test_list_voices_nonexistent(tmp_path):
    result = list_voices(tmp_path / "nope")
    assert result == []


def test_resolve_voice_exact(tmp_path):
    wav = tmp_path / "zack.wav"
    wav.touch()
    assert resolve_voice("zack", tmp_path) == wav


def test_resolve_voice_case_insensitive(tmp_path):
    wav = tmp_path / "Adrian.wav"
    wav.touch()
    result = resolve_voice("adrian", tmp_path)
    assert result == wav


def test_resolve_voice_missing(tmp_path):
    with pytest.raises(Exception, match="no voice file found for 'adrian'"):
        resolve_voice("adrian", tmp_path)


def test_resolve_voice_error_message_format(tmp_path):
    with pytest.raises(
        Exception, match=r"expected.*voices/adrian\.wav"
    ):
        resolve_voice("adrian", tmp_path / "voices")


def test_premade_voices_count():
    assert len(PREMADE_VOICES) == 28


def test_install_voices_skips_existing(tmp_path, mocker):
    # Pre-create all voices so all are skipped
    for name in PREMADE_VOICES:
        (tmp_path / f"{name.lower()}.wav").touch()

    mock_stream = mocker.patch("narrate.voices.httpx.stream")
    install_voices(tmp_path)
    mock_stream.assert_not_called()


def test_install_voices_singular_grammar(tmp_path, mocker, capsys):
    """When exactly 1 voice is downloaded and rest skipped, use singular."""
    # Pre-create all but one voice
    for name in PREMADE_VOICES[1:]:
        (tmp_path / f"{name.lower()}.wav").touch()

    mock_response = mocker.MagicMock()
    mock_response.raise_for_status = mocker.MagicMock()
    mock_response.iter_bytes.return_value = [b"RIFF" + b"\x00" * 100]
    mock_response.__enter__ = mocker.MagicMock(return_value=mock_response)
    mock_response.__exit__ = mocker.MagicMock(return_value=False)
    mocker.patch("narrate.voices.httpx.stream", return_value=mock_response)

    install_voices(tmp_path)
    captured = capsys.readouterr()
    assert "1 voice," in captured.out
    assert "27 voices existing" in captured.out


def test_install_voices_downloads(tmp_path, mocker):
    # Mock httpx.stream as context manager
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status = mocker.MagicMock()
    mock_response.iter_bytes.return_value = [b"RIFF" + b"\x00" * 100]
    mock_response.__enter__ = mocker.MagicMock(return_value=mock_response)
    mock_response.__exit__ = mocker.MagicMock(return_value=False)

    mocker.patch("narrate.voices.httpx.stream", return_value=mock_response)
    install_voices(tmp_path)

    # All 28 should have been "downloaded"
    wav_files = list(tmp_path.glob("*.wav"))
    assert len(wav_files) == 28
