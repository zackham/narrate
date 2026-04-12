"""Tests for narrate.parser."""

import click
import pytest

from narrate.parser import Turn, parse_script, parse_text


def test_jsonl_valid(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text(
        '{"voice": "zack", "text": "Hello."}\n'
        '{"voice": "adrian", "text": "Hi there."}\n'
    )
    turns = parse_script(f)
    assert turns == [
        Turn(voice="zack", text="Hello."),
        Turn(voice="adrian", text="Hi there."),
    ]


def test_jsonl_with_empty_lines(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text(
        '{"voice": "zack", "text": "Line one."}\n'
        "\n"
        '{"voice": "adrian", "text": "Line two."}\n'
        "\n"
    )
    turns = parse_script(f)
    assert len(turns) == 2


def test_elevenlabs_json_unwrap(tmp_path):
    f = tmp_path / "script.json"
    f.write_text(
        '{"inputs": ['
        '{"voice": "zack", "text": "So here is the thing."},'
        '{"voice": "adrian", "text": "Yeah, I agree."}'
        "]}"
    )
    turns = parse_script(f)
    assert len(turns) == 2
    assert turns[0].voice == "zack"
    assert turns[1].voice == "adrian"


def test_plain_text_fallback(tmp_path):
    f = tmp_path / "essay.txt"
    f.write_text("This is a plain text essay about something.")
    turns = parse_script(f, default_voice="zack")
    assert len(turns) == 1
    assert turns[0].voice == "zack"
    assert turns[0].text == "This is a plain text essay about something."


def test_default_voice_applied(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text('{"text": "No voice specified."}\n')
    turns = parse_script(f, default_voice="zack")
    assert turns[0].voice == "zack"


def test_missing_voice_error(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text('{"text": "No voice."}\n')
    with pytest.raises(Exception, match="--voice is required"):
        parse_script(f)


def test_expression_tag_preservation(tmp_path):
    f = tmp_path / "script.jsonl"
    f.write_text(
        '{"voice": "zack", "text": "So here is the thing. [laugh] It is obvious."}\n'
    )
    turns = parse_script(f)
    assert "[laugh]" in turns[0].text


def test_empty_file_error(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    with pytest.raises(Exception, match="empty"):
        parse_script(f)


def test_parse_text_inline():
    turns = parse_text("Hello world", "zack")
    assert turns == [Turn(voice="zack", text="Hello world")]


def test_malformed_json_falls_back_to_text(tmp_path, capsys):
    f = tmp_path / "bad.jsonl"
    f.write_text("this is not json at all\nneither is this")
    turns = parse_script(f, default_voice="zack")
    assert len(turns) == 1
    assert turns[0].voice == "zack"
    captured = capsys.readouterr()
    assert "could not parse as JSONL, treating as plain text" in captured.err


def test_jsonl_missing_text_field_raises(tmp_path):
    """JSON that parses but is missing 'text' should raise, not fall through to plain text."""
    f = tmp_path / "bad.jsonl"
    f.write_text('{"voice": "zack", "content": "Hello."}\n')
    with pytest.raises(click.ClickException, match="missing required field 'text'"):
        parse_script(f)


def test_elevenlabs_json_missing_text_raises(tmp_path):
    """ElevenLabs format with missing 'text' should raise."""
    f = tmp_path / "script.json"
    f.write_text('{"inputs": [{"voice": "zack"}]}')
    with pytest.raises(click.ClickException, match="missing required field 'text'"):
        parse_script(f)
