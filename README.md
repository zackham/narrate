# narrate

Turn a script into a multi-voice audio file with one command. Runs locally, costs nothing.

Chatterbox TTS can clone a voice from a 10-second clip and produce audio comparable to ElevenLabs. But using it directly means writing Python, managing per-speaker generation, chunking long text so the model doesn't choke, stitching segments together with silence gaps, normalizing loudness, and handling a dozen upstream library quirks. narrate does all of that for you.

**What you get:**
- **Script in, audio out.** Pass a JSONL file with speaker labels and text, get a single MP3. No Python required.
- **Multi-speaker.** Each line can use a different voice. Voices are just WAV files in a directory.
- **Smart chunking.** Long text is split at sentence boundaries to stay within model limits, then stitched seamlessly.
- **Expression tags.** `[laugh]`, `[sigh]`, `[whisper]` — inline in your text, passed through to the engine.
- **Voice library.** 28 pre-made voices downloadable with one command, or clone your own from any audio clip.
- **Engine-agnostic.** Ships with Chatterbox (local, free) and ElevenLabs (cloud, paid) backends. Same script format for both — swap engines with a flag.
- **Clean output.** No upstream library warnings, no progress bar spam. Just your audio.

Powered by [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) (Resemble AI, MIT license).

## Install

```bash
curl -sSL https://raw.githubusercontent.com/zackham/narrate/master/install.sh | bash
```

Or if you already have [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/zackham/narrate.git
```

## Quick Start

```bash
# Download pre-made voices (~28 voices)
narrate install-voices

# Create a script
cat > script.jsonl << 'EOF'
{"voice": "jordan", "text": "Wait, so I can just write a script and get a multi-voice podcast out of it?"}
{"voice": "adrian", "text": "One command. It chunks your text, generates each speaker, stitches it together, normalizes the audio."}
{"voice": "olivia", "text": "And it runs locally. No API keys, no billing, no rate limits. [chuckle] I was mass-producing podcasts on ElevenLabs before this. My credit card is relieved."}
{"voice": "jordan", "text": "[gasp] OK so what's the catch?"}
{"voice": "adrian", "text": "There isn't one. It's open source. You just need a ten second voice clip and you're cloning."}
EOF

# Generate
narrate script.jsonl -o podcast.mp3
```

## Voice Setup

### Option 1: Pre-made Voices

Download ~28 pre-made voices with a single command:

```bash
narrate install-voices
```

This downloads voices from [devnen/Chatterbox-TTS-Server](https://github.com/devnen/Chatterbox-TTS-Server) (MIT license) into `~/.narrate/voices/`.

### Option 2: Your Own Voices

Drop WAV files (10-30 second reference clips) into `~/.narrate/voices/`:

```
~/.narrate/voices/
  zack.wav
  adrian.wav
  olivia.wav
```

The `voice` field in your script maps to the filename (e.g. `"voice": "zack"` → `~/.narrate/voices/zack.wav`). Voice matching is case-insensitive. Clips must be at least 5 seconds long.

Override the voices directory with `--voices-dir` or in `narrate.toml`.

### List Available Voices

```bash
narrate voices
```

## Script Formats

### JSONL (primary)

```jsonl
{"voice": "adrian", "text": "So here's the thing. [laugh] It's obvious in hindsight."}
{"voice": "olivia", "text": "Yeah, I had the same reaction. [sigh] But nobody talks about it."}
```

### ElevenLabs-Compatible JSON

```json
{
  "inputs": [
    {"voice": "adrian", "text": "So here's the thing."},
    {"voice": "olivia", "text": "Yeah, I agree."}
  ]
}
```

### Plain Text

```bash
narrate essay.txt --voice adrian -o output.mp3
```

### Inline Text

```bash
narrate --text "Hello world" --voice adrian -o hello.mp3
```

## Expression Tags

Chatterbox supports inline expression tags that control vocal delivery:

| Tag | Effect |
|-----|--------|
| `[laugh]` | Laughter |
| `[chuckle]` | Chuckle |
| `[sigh]` | Sigh |
| `[gasp]` | Gasp |
| `[cough]` | Cough |
| `[groan]` | Groan |
| `[sniff]` | Sniff |
| `[shush]` | Shush |
| `[clear throat]` | Throat clearing |
| `[yawn]` | Yawn |
| `[whisper]` | Whispered speech |

Use them inline: `"So here's the thing. [laugh] It's obvious in hindsight."`

## Pauses & Silence

Insert clean silence into your script without synthesizing speech. Useful for dramatic pauses, section breaks, or pacing.

### Explicit pause with `pause_seconds`

Add a JSONL entry with `pause_seconds` to insert an exact duration of silence:

```jsonl
{"voice": "adrian", "text": "Let that sink in for a moment."}
{"voice": "", "text": "", "pause_seconds": 3.0}
{"voice": "adrian", "text": "OK. Moving on."}
```

The `pause_seconds` field works in both JSONL and ElevenLabs JSON formats. The `voice` and `text` fields can be empty strings.

### Implicit silence

These patterns also produce silence (using the `turn_gap` duration):

- **Empty text**: `{"voice": "adrian", "text": ""}`
- **Ellipsis**: `{"voice": "adrian", "text": "..."}`
- **Empty voice**: `{"voice": "", "text": "anything"}`

This means entries with missing or empty voices won't crash — they produce a brief pause instead.

## Engine Configuration

### Chatterbox (default, local)

No configuration needed. Runs locally on CPU or CUDA. First run downloads the model (~1.4GB) from HuggingFace.

```bash
# Use GPU
narrate script.jsonl -o output.mp3 --device cuda

# Force CPU
narrate script.jsonl -o output.mp3 --device cpu
```

### ElevenLabs (cloud, requires API key)

```bash
export ELEVENLABS_API_KEY="your-key-here"
narrate script.jsonl --engine elevenlabs -o output.wav
```

Configure voice ID mapping in `~/.narrate/narrate.toml`:

```toml
[elevenlabs]
api_key = ""  # or use ELEVENLABS_API_KEY env var
voice_map = { adrian = "21m00Tcm4TlvDq8ikWAM", olivia = "voice_id_here" }
```

## Configuration

narrate looks for config in two places (working directory overrides global):

1. `./narrate.toml` (project-local)
2. `~/.narrate/narrate.toml` (global default)

```toml
[voices]
dir = "~/.narrate/voices"
default = "adrian"

[output]
format = "mp3"
turn_gap = 0.4

[engine]
default = "chatterbox"
device = "auto"  # auto | cpu | cuda

[elevenlabs]
api_key = ""
voice_map = { adrian = "voice_id_here" }
```

CLI flags override config file values.

## CLI Reference

```
narrate [FILE] [OPTIONS]
narrate install-voices [--voices-dir DIR]
narrate voices [--voices-dir DIR]

Options:
  FILE                    Script file (JSONL, JSON, or plain text)
  --text TEXT             Inline text to synthesize
  --voice NAME            Default voice name
  --voices-dir DIR        Voice WAV files directory (default: ~/.narrate/voices)
  --engine ENGINE         TTS engine: chatterbox, elevenlabs
  --device DEVICE         Device: auto, cpu, cuda
  -o, --output PATH       Output file path (default: INPUT.mp3 or output.mp3)
  --format FORMAT         Output format: wav, mp3
  --turn-gap SECONDS      Silence between speaker turns (default: 0.4)
  --no-normalize          Disable LUFS audio normalization
  --help                  Show help
```

## Troubleshooting

**"voice clip 'X' is N.Ns -- must be at least 5 seconds"**
Your voice reference WAV is too short. Chatterbox needs at least 5 seconds of speech. Record or find a longer clip (10-30 seconds with varied intonation is ideal).

**"ffmpeg not found"**
MP3 output requires ffmpeg. Install it via your package manager (`brew install ffmpeg`, `apt install ffmpeg`, etc.) or use `--format wav`.

**"no voice file found for 'X'"**
The voice WAV file is missing from your voices directory. Run `narrate install-voices` to download pre-made voices, or add your own WAV file.

**"CUDA device requested but no GPU available"**
Use `--device cpu` or `--device auto` (default) to run on CPU.

**First run is slow**
Chatterbox downloads the model (~1.4GB) from HuggingFace on first use. Subsequent runs use the cached model.

**ElevenLabs errors**
- 401: Check your API key (`ELEVENLABS_API_KEY` env var or `narrate.toml`)
- 429: Rate limit exceeded. Wait and retry, or check your plan quota.
- Voice not configured: Add the voice ID to `[elevenlabs.voice_map]` in `narrate.toml`

## License

MIT
