"""Tests for narrate.pipeline."""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from narrate.parser import Turn
from narrate.pipeline import _infer_format, chunk_text, generate_audio, write_output


class TestChunkText:
    def test_short_text_no_split(self):
        result = chunk_text("Hello world.")
        assert result == ["Hello world."]

    def test_multi_sentence_merge(self):
        text = "First sentence. Second sentence. Third sentence."
        result = chunk_text(text, max_chars=280)
        assert len(result) == 1
        assert result[0] == text

    def test_multi_sentence_split(self):
        text = "A" * 200 + ". " + "B" * 200 + "."
        result = chunk_text(text, max_chars=280)
        assert len(result) == 2

    def test_long_sentence_split_at_space(self):
        text = " ".join(["word"] * 100)  # ~499 chars
        result = chunk_text(text, max_chars=50)
        for chunk in result:
            assert len(chunk) <= 50

    def test_expression_tags_preserved(self):
        text = "So here is the thing. [laugh] It is obvious in hindsight."
        result = chunk_text(text)
        full = " ".join(result)
        assert "[laugh]" in full

    def test_empty_text(self):
        result = chunk_text("")
        assert result == [""]


class TestGenerateAudio:
    def _make_engine(self, needs_wav=True):
        engine = MagicMock()
        engine.needs_wav = needs_wav
        engine.generate.return_value = (24000, np.ones(2400))
        return engine

    def test_single_turn(self, tmp_path):
        (tmp_path / "zack.wav").touch()
        engine = self._make_engine()
        turns = [Turn(voice="zack", text="Hello.")]
        sr, audio = generate_audio(turns, engine, tmp_path, normalize=False)
        assert sr == 24000
        assert len(audio) > 0
        engine.generate.assert_called_once()

    def test_multi_turn_gap(self, tmp_path):
        (tmp_path / "zack.wav").touch()
        (tmp_path / "adrian.wav").touch()
        engine = self._make_engine()
        turns = [
            Turn(voice="zack", text="Hello."),
            Turn(voice="adrian", text="Hi."),
        ]
        sr, audio = generate_audio(
            turns, engine, tmp_path, turn_gap=0.4, normalize=False
        )
        # Expected: 2400 (turn1) + 9600 (gap) + 2400 (turn2) = 14400
        expected_gap = int(24000 * 0.4)
        assert expected_gap == 9600
        assert len(audio) == 2400 + expected_gap + 2400

    def test_gap_is_silence(self, tmp_path):
        (tmp_path / "zack.wav").touch()
        (tmp_path / "adrian.wav").touch()
        engine = self._make_engine()
        turns = [
            Turn(voice="zack", text="Hello."),
            Turn(voice="adrian", text="Hi."),
        ]
        sr, audio = generate_audio(
            turns, engine, tmp_path, turn_gap=0.4, normalize=False
        )
        gap_start = 2400
        gap_end = 2400 + 9600
        gap = audio[gap_start:gap_end]
        assert np.all(gap == 0.0)

    def test_engine_without_wav_skips_resolve(self, tmp_path):
        """An engine with needs_wav=False should receive the voice name, not a Path."""
        engine = self._make_engine(needs_wav=False)
        turns = [Turn(voice="zack", text="Hello.")]
        sr, audio = generate_audio(turns, engine, tmp_path, normalize=False)
        # The voice_ref passed to engine.generate should be the string "zack"
        call_args = engine.generate.call_args
        assert call_args[0][1] == "zack"


class TestWriteOutput:
    def test_wav_output(self, tmp_path):
        audio = np.random.randn(24000).astype(np.float32)
        out = tmp_path / "test.wav"
        write_output(24000, audio, out, fmt="wav")
        assert out.exists()
        assert out.stat().st_size > 0

    def test_creates_parent_dirs(self, tmp_path):
        audio = np.random.randn(24000).astype(np.float32)
        out = tmp_path / "nested" / "deep" / "test.wav"
        write_output(24000, audio, out)
        assert out.exists()

    def test_infer_wav_from_extension(self, tmp_path):
        audio = np.random.randn(24000).astype(np.float32)
        out = tmp_path / "test.wav"
        write_output(24000, audio, out)  # no fmt — should infer wav
        assert out.exists()


class TestInferFormat:
    def test_infer_wav(self):
        assert _infer_format(Path("out.wav"), None) == "wav"

    def test_infer_mp3(self):
        assert _infer_format(Path("out.mp3"), None) == "mp3"

    def test_explicit_overrides(self):
        assert _infer_format(Path("out.wav"), "mp3") == "mp3"

    def test_unknown_ext_defaults_wav(self):
        assert _infer_format(Path("out.ogg"), None) == "wav"
