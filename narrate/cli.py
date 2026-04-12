"""CLI entry point for narrate."""

from __future__ import annotations

from pathlib import Path

import click

from narrate import __version__
from narrate.config import DEFAULT_VOICES_DIR, load_config
from narrate.engine import get_engine
from narrate.parser import parse_script, parse_text
from narrate.pipeline import chunk_text, generate_audio, write_output
from narrate.voices import PREMADE_VOICES, install_voices, list_voices


class NarrateGroup(click.Group):
    """Group that defaults to the 'generate' command when no subcommand matches."""

    def resolve_command(self, ctx: click.Context, args: list[str]) -> tuple:
        # If args are empty or the first arg is not a known subcommand,
        # route to the hidden 'generate' command
        cmd_name = click.utils.make_str(args[0]) if args else None
        if cmd_name is None or cmd_name not in self.commands:
            return "generate", self.commands["generate"], args
        return super().resolve_command(ctx, args)


@click.group(
    cls=NarrateGroup,
    context_settings={"ignore_unknown_options": True},
)
@click.version_option(version=__version__, prog_name="narrate")
def cli() -> None:
    """narrate -- Convert multi-speaker scripts to audio using local TTS."""
    pass


@cli.command("generate")
@click.argument("file", required=False, type=click.Path(exists=True))
@click.option("--text", default=None, help="Inline text to synthesize.")
@click.option("--voice", default=None, help="Default voice name.")
@click.option(
    "--voices-dir",
    default=None,
    type=click.Path(),
    help="Directory containing voice WAV files.",
)
@click.option(
    "--engine",
    "engine_name",
    default=None,
    type=click.Choice(["chatterbox", "elevenlabs"]),
    help="TTS engine to use.",
)
@click.option(
    "--device",
    default=None,
    type=click.Choice(["auto", "cpu", "cuda"]),
    help="Device for local TTS.",
)
@click.option("-o", "--output", default=None, type=click.Path(), help="Output file path.")
@click.option(
    "--format",
    "fmt",
    default=None,
    type=click.Choice(["wav", "mp3"]),
    help="Output format.",
)
@click.option("--turn-gap", default=None, type=float, help="Silence between turns (seconds).")
@click.option("--no-normalize", is_flag=True, default=False, help="Disable LUFS normalization.")
def generate(
    file: str | None,
    text: str | None,
    voice: str | None,
    voices_dir: str | None,
    engine_name: str | None,
    device: str | None,
    output: str | None,
    fmt: str | None,
    turn_gap: float | None,
    no_normalize: bool,
) -> None:
    """Generate audio from a script or inline text."""
    # Validate mutual exclusivity
    if file and text:
        raise click.UsageError("Provide either FILE or --text, not both")
    if not file and not text:
        raise click.UsageError("Provide a script file or use --text")
    if not output:
        if file:
            output = str(Path(file).with_suffix(".mp3"))
        else:
            output = "output.mp3"

    # Load config and merge CLI flags
    config = load_config()
    if voices_dir is not None:
        config.voices_dir = Path(voices_dir)
    if voice is not None:
        config.default_voice = voice
    if engine_name is not None:
        config.engine = engine_name
    if device is not None:
        config.device = device
    if fmt is not None:
        config.output_format = fmt
    if turn_gap is not None:
        config.turn_gap = turn_gap

    # Parse input
    if text:
        if not voice and not config.default_voice:
            raise click.UsageError("--voice is required with --text")
        turns = parse_text(text, voice or config.default_voice)
    else:
        turns = parse_script(Path(file), default_voice=config.default_voice)

    # Count total chunks for progress
    total_chunks = sum(len(chunk_text(t.text)) for t in turns)

    # Build engine and generate
    engine = get_engine(config.engine, config)

    with click.progressbar(length=total_chunks, label="Generating audio") as bar:
        sr, audio = generate_audio(
            turns,
            engine,
            config.voices_dir,
            turn_gap=config.turn_gap,
            normalize=not no_normalize,
            progress_callback=bar.update,
        )

    # Pass explicit format if CLI or config set one, else let write_output infer from extension
    explicit_fmt = fmt if fmt is not None else None
    write_output(sr, audio, Path(output), fmt=explicit_fmt)
    click.echo(f"Written to {output}")


@cli.command("install-voices")
@click.option(
    "--voices-dir",
    default=None,
    type=click.Path(),
    help="Directory to install voices into.",
)
def install_voices_cmd(voices_dir: str | None) -> None:
    """Download pre-made voice library (~28 voices)."""
    vdir = Path(voices_dir) if voices_dir else DEFAULT_VOICES_DIR
    vdir.mkdir(parents=True, exist_ok=True)
    with click.progressbar(length=len(PREMADE_VOICES), label="Downloading voices") as bar:
        install_voices(vdir, progress_callback=bar.update)
    click.echo(f"Voices installed to {vdir}")


@cli.command("voices")
@click.option(
    "--voices-dir",
    default=None,
    type=click.Path(),
    help="Directory containing voice WAV files.",
)
def voices_cmd(voices_dir: str | None) -> None:
    """List available voices."""
    vdir = Path(voices_dir) if voices_dir else DEFAULT_VOICES_DIR
    names = list_voices(vdir)
    if not names:
        click.echo("No voices found. Run 'narrate install-voices' to download voices.")
        return
    for name in names:
        click.echo(name)
