"""Voice Clone client — communicates with the Coqui XTTS HTTP server."""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import urllib.request

logger = logging.getLogger("mega-brain")

VOICE_CLONE_URL = os.getenv("VOICE_CLONE_URL", "http://127.0.0.1:9876")
TTS_CACHE_DIR = Path(__file__).parent.parent / "data" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _call(method: str, **kwargs) -> dict:
    data = json.dumps(kwargs).encode()
    req = urllib.request.Request(
        f"{VOICE_CLONE_URL}/{method}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def is_available() -> bool:
    try:
        req = urllib.request.Request(f"{VOICE_CLONE_URL}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read()).get("model_loaded", False)
    except Exception:
        return False


def clone(text: str, language: str = "pt", voice: str = "") -> bytes:
    """Clone voice from reference audio. Returns WAV bytes."""
    key = f"{text}:{language}:{voice or language}"
    cache_key = hashlib.md5(key.encode()).hexdigest()
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"

    if cache_path.exists():
        return cache_path.read_bytes()

    result = _call("clone", text=text, language=language, voice=voice or language)
    if "error" in result or "audio" not in result:
        logger.error(f"Erro clone de voz: {result.get('error', 'desconhecido')}")
        return b""

    wav_bytes = base64.b64decode(result["audio"])
    cache_path.write_bytes(wav_bytes)
    return wav_bytes


def health() -> dict:
    try:
        req = urllib.request.Request(f"{VOICE_CLONE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}
