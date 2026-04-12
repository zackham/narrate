"""Script parsing for narrate — JSONL, ElevenLabs JSON, and plain text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import click


class Turn(NamedTuple):
    voice: str | None
    text: str


def parse_script(path: Path, default_voice: str | None = None) -> list[Turn]:
    """Parse a script file into a list of Turns.

    Detection logic:
    1. Try JSON — if dict with 'inputs' list, unwrap (ElevenLabs format).
    2. Otherwise try each line as JSON (JSONL format).
    3. If all JSON fails, treat as plain text with default_voice.
    """
    content = path.read_text().strip()
    if not content:
        raise click.ClickException(f"script file is empty: {path}")

    # Try ElevenLabs JSON format
    try:
        data = json.loads(content)
        if isinstance(data, dict) and isinstance(data.get("inputs"), list):
            turns: list[Turn] = []
            for i, item in enumerate(data["inputs"]):
                if not isinstance(item, dict):
                    raise click.ClickException(
                        f"inputs[{i}]: expected object, got {type(item).__name__}"
                    )
                if "text" not in item:
                    raise click.ClickException(
                        f"inputs[{i}]: missing required field 'text'"
                    )
                turns.append(Turn(voice=item.get("voice"), text=item["text"]))
            return _apply_default_voice(turns, default_voice)
    except json.JSONDecodeError:
        pass

    # Try JSONL format
    lines = [line for line in content.split("\n") if line.strip()]
    jsonl_turns: list[Turn] = []
    jsonl_ok = True
    for lineno, line in enumerate(lines, 1):
        try:
            item = json.loads(line)
            if isinstance(item, dict) and "text" not in item:
                raise click.ClickException(
                    f"line {lineno}: missing required field 'text'"
                )
            jsonl_turns.append(Turn(voice=item.get("voice"), text=item["text"]))
        except json.JSONDecodeError:
            jsonl_ok = False
            break

    if jsonl_ok and jsonl_turns:
        return _apply_default_voice(jsonl_turns, default_voice)

    # Plain text fallback
    click.echo("Warning: could not parse as JSONL, treating as plain text", err=True)
    return _apply_default_voice([Turn(voice=None, text=content)], default_voice)


def parse_text(text: str, voice: str) -> list[Turn]:
    """Create a single Turn from inline text."""
    return [Turn(voice=voice, text=text)]


def _apply_default_voice(
    turns: list[Turn], default_voice: str | None
) -> list[Turn]:
    """Apply default voice to turns missing a voice field."""
    result = []
    for turn in turns:
        if turn.voice is None:
            if default_voice is None:
                raise click.ClickException(
                    "--voice is required for scripts without voice fields"
                )
            result.append(Turn(voice=default_voice, text=turn.text))
        else:
            result.append(turn)
    return result
