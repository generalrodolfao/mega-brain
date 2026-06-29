"""J.A.R.V.I.S. Voice Engine — Voice Clone (XTTS) with edge-tts fallback."""

import asyncio
import io
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger("mega-brain")

CACHE_DIR = Path(tempfile.gettempdir()) / "megabrain_tts"
CACHE_DIR.mkdir(exist_ok=True)

# Pre-processed J.A.R.V.I.S. profile (edge-tts fallback)
DEFAULT_VOICE = "pt-BR-AntonioNeural"
TTS_RATE = "+0%"
TTS_PITCH = "+0Hz"
TTS_VOLUME = "+0%"

FFMPEG_FILTERS = [
    "loudnorm=I=-16:LRA=11:TP=-1.5",
]

VOICE_LANG_MAP = {
    "pt": "pt",
    "pt-BR": "pt",
    "en": "en",
    "en-US": "en",
    "en-GB": "en",
}


async def generate_speech(text: str, voice: str = DEFAULT_VOICE, use_clone: bool = True, stream: bool = False) -> bytes:
    """Generate J.A.R.V.I.S. speech. Uses voice clone (XTTS) when available, falls back to edge-tts."""

    # Try voice clone first
    if use_clone:
        try:
            from core.voice_clone import is_available, clone
            if is_available():
                lang = VOICE_LANG_MAP.get(voice, "pt")
                result = clone(text, language=lang)
                if result:
                    # Convert WAV to MP3 for streaming
                    return wav_to_mp3(result)
        except Exception as e:
            logger.debug(f"Voice clone unavailable, falling back to edge-tts: {e}")

    # Fallback to edge-tts
    return await _edge_tts(text, voice, stream=stream)


async def _edge_tts(text: str, voice: str = DEFAULT_VOICE, stream: bool = False) -> bytes:
    import edge_tts

    cache_key = _hash(f"{voice}|{TTS_RATE}|{TTS_PITCH}|{text}")
    cache_file = CACHE_DIR / f"{cache_key}.mp3"
    if cache_file.exists():
        logger.debug(f"  TTS cache hit")
        return cache_file.read_bytes()

    logger.info(f"  TTS (edge-tts): '{text[:60]}...' | {voice}")

    try:
        communicate = edge_tts.Communicate(text, voice, rate=TTS_RATE, pitch=TTS_PITCH, volume=TTS_VOLUME)

        if stream:
            return communicate

        base = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                base.write(chunk["data"])
        mp3 = base.getvalue()
        if not mp3:
            return b""
        processed = _apply_filters(mp3)
        cache_file.write_bytes(processed)
        return processed
    except Exception as e:
        logger.error(f"  Erro TTS edge-tts: {e}")
        return b""


def wav_to_mp3(wav_bytes: bytes) -> bytes:
    import subprocess
    cmd = [
        "ffmpeg", "-i", "pipe:0",
        "-af", ",".join(FFMPEG_FILTERS),
        "-acodec", "libmp3lame", "-b:a", "96k",
        "-f", "mp3", "pipe:1",
        "-y", "-loglevel", "error",
    ]
    try:
        r = subprocess.run(cmd, input=wav_bytes, capture_output=True, timeout=30)
        return r.stdout if (r.returncode == 0 and r.stdout) else wav_bytes
    except Exception:
        return wav_bytes


def _apply_filters(mp3_data: bytes) -> bytes:
    import subprocess
    cmd = [
        "ffmpeg", "-i", "pipe:0",
        "-af", ",".join(FFMPEG_FILTERS),
        "-acodec", "libmp3lame", "-b:a", "96k",
        "-f", "mp3", "pipe:1",
        "-y", "-loglevel", "error",
    ]
    try:
        r = subprocess.run(cmd, input=mp3_data, capture_output=True, timeout=20)
        return r.stdout if (r.returncode == 0 and r.stdout) else mp3_data
    except Exception:
        return mp3_data


def _hash(s: str) -> str:
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()


async def test_voice(text: str = "Olá. Sou o J.A.R.V.I.S., seu assistente Mega Brain."):
    audio = await generate_speech(text)
    if audio:
        logger.info(f"  OK: {len(audio)} bytes")
        (CACHE_DIR / "test_output.mp3").write_bytes(audio)
    else:
        logger.error("  FALHOU")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_voice())
