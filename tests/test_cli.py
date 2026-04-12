"""Tests for narrate.cli."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from click.testing import CliRunner

from narrate.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "narrate" in result.output
    assert "generate" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_voices_subcommand(tmp_path):
    (tmp_path / "alice.wav").touch()
    (tmp_path / "bob.wav").touch()
    runner = CliRunner()
    result = runner.invoke(cli, ["voices", "--voices-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "bob" in result.output


def test_voices_empty(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["voices", "--voices-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No voices found" in result.output


def test_missing_file_error():
    runner = CliRunner()
    result = runner.invoke(cli, ["nonexistent.jsonl", "-o", "out.wav"])
    assert result.exit_code != 0


def test_no_input_error():
    runner = CliRunner()
    result = runner.invoke(cli, ["-o", "out.wav"])
    assert result.exit_code != 0
    assert "Provide a script file or use --text" in result.output


def test_both_file_and_text_error(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text('{"voice": "zack", "text": "Hello."}\n')
    runner = CliRunner()
    result = runner.invoke(cli, [str(f), "--text", "hello", "-o", "out.wav"])
    assert result.exit_code != 0
    assert "not both" in result.output


@patch("narrate.cli.get_engine")
@patch("narrate.cli.generate_audio")
@patch("narrate.cli.write_output")
def test_default_output_from_input_filename(
    mock_write, mock_generate, mock_get_engine, tmp_path
):
    """When -o is omitted, output defaults to input stem + .mp3."""
    script = tmp_path / "episode.jsonl"
    script.write_text('{"voice": "zack", "text": "Hello."}\n')
    voice_file = tmp_path / "zack.wav"
    voice_file.touch()

    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_generate.return_value = (24000, np.ones(24000))

    runner = CliRunner()
    result = runner.invoke(
        cli, [str(script), "--voices-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    # write_output should be called with a path ending in episode.wav
    written_path = mock_write.call_args[0][2]
    assert written_path.name == "episode.mp3"


@patch("narrate.cli.get_engine")
@patch("narrate.cli.generate_audio")
@patch("narrate.cli.write_output")
def test_default_output_for_text_mode(
    mock_write, mock_generate, mock_get_engine, tmp_path
):
    """When --text is used without -o, output defaults to output.mp3."""
    voice_file = tmp_path / "zack.wav"
    voice_file.touch()

    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_generate.return_value = (24000, np.ones(24000))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--text", "Hello world", "--voice", "zack", "--voices-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    written_path = mock_write.call_args[0][2]
    assert written_path.name == "output.mp3"


def test_text_requires_voice():
    runner = CliRunner()
    result = runner.invoke(cli, ["--text", "hello", "-o", "out.wav"])
    assert result.exit_code != 0
    assert "--voice is required" in result.output


@patch("narrate.cli.get_engine")
@patch("narrate.cli.generate_audio")
@patch("narrate.cli.write_output")
def test_main_flow_with_mock_engine(
    mock_write, mock_generate, mock_get_engine, tmp_path
):
    # Setup
    script = tmp_path / "script.jsonl"
    script.write_text('{"voice": "zack", "text": "Hello world."}\n')
    voice_file = tmp_path / "zack.wav"
    voice_file.touch()
    output = tmp_path / "out.wav"

    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_generate.return_value = (24000, np.ones(24000))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [str(script), "--voices-dir", str(tmp_path), "-o", str(output)],
    )
    assert result.exit_code == 0, result.output
    mock_generate.assert_called_once()
    mock_write.assert_called_once()
