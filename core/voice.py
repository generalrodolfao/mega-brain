"""
Voice Module — Whisper STT integration for the Mega Brain.

Converts voice input to text for processing through the
sentiment router and pipeline.

The Whisper model is loaded ONCE as a module-level singleton
so subsequent transcriptions are near-instant.
"""

import io
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mega-brain")

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Module-level singleton — model loads once, reuse forever
_whisper_model = None

def get_whisper_model(model_size: str = "tiny"):
    global _whisper_model
    if _whisper_model is None:
        if not HAS_WHISPER:
            raise RuntimeError("whisper not installed")
        import torch
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Carregando modelo Whisper ({model_size}) em {device}...")
        _whisper_model = whisper.load_model(model_size, device=device)
    return _whisper_model


class VoiceInput:
    """
    Handles voice capture and transcription.
    Supports local Whisper, OpenAI Whisper API, and file input.
    """

    def __init__(self, model_size: str = "tiny", use_api: bool = False):
        self.model_size = model_size
        self.use_api = use_api
        self.model = None
        self.openai_client = None

        if not use_api and HAS_WHISPER:
            self.model = get_whisper_model(model_size)
        elif use_api and HAS_OPENAI:
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def list_microphones() -> list:
        """List available microphones."""
        if not HAS_PYAUDIO:
            print("  pyaudio not installed. Run: pip install pyaudio")
            return []
        
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({"index": i, "name": info["name"]})
        p.terminate()
        return devices

    def transcribe_file(self, audio_path: str, language: str = "pt") -> str:
        """Transcribe an audio file to text."""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.use_api and self.openai_client:
            with open(audio_path, "rb") as f:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                )
            return transcript.text

        if self.model:
            result = self.model.transcribe(audio_path, language=language)
            return result["text"].strip()

        raise RuntimeError("No transcription backend available. Install whisper or set use_api=True.")

    def transcribe_mic(self, duration: int = 5, sample_rate: int = 16000) -> str:
        """Record from microphone and transcribe."""
        if not HAS_PYAUDIO:
            raise ImportError("pyaudio required for mic recording. pip install pyaudio")

        import numpy as np
        import wave

        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=1024,
        )

        print(f"  Recording for {duration}s...")
        frames = []
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)
        print("  Recording finished.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        temp_file = Path("/tmp/mega_brain_input.wav")
        with wave.open(str(temp_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(frames))

        return self.transcribe_file(str(temp_file))
