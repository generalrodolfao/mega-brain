#!/tmp/coqui-venv/bin/python3
"""Voice Clone Server — Coqui XTTS-v2 via socket pair (stdin/stdout protocol)."""

import os, sys, json, base64, struct, logging, signal, traceback, tempfile

logging.basicConfig(level=logging.INFO, format="[VOICE] %(message)s", stream=sys.stderr)
log = logging.getLogger("voice-clone")

REF_FILES = {
    "pt": "/Users/rodolfo/projetos/mega_brain/audio/JARVIS START UP.mp3",
    "en": "/Users/rodolfo/projetos/mega_brain/audio/JARVIS - Marvel's Iron Man 3 Second Screen Experience - Trailer.mp3",
}

MODEL = None

def load_model():
    global MODEL
    os.environ["COQUI_TOS_AGREED"] = "1"
    import torch
    _orig_load = torch.load
    def _patched_load(f, *a, **kw):
        kw.setdefault("weights_only", False)
        return _orig_load(f, *a, **kw)
    torch.load = _patched_load
    from TTS.tts.configs.xtts_config import XttsConfig
    torch.serialization.add_safe_globals([XttsConfig])
    from TTS.api import TTS
    log.info("Loading XTTS-v2...")
    MODEL = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
    log.info("XTTS-v2 ready")

def handle(text: str, language: str, voice: str) -> dict:
    ref = REF_FILES.get(voice, REF_FILES.get(language, REF_FILES["pt"]))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        MODEL.tts_to_file(text=text, file_path=tmp_path, speaker_wav=ref, language=language)
        with open(tmp_path, "rb") as f:
            wav_data = f.read()
        return {"audio": base64.b64encode(wav_data).decode(), "size": len(wav_data), "format": "wav"}
    except Exception as e:
        log.error(f"Clone error: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}
    finally:
        try: os.unlink(tmp_path)
        except: pass

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: voice_clone_server.py [--http PORT]")
        return

    if "--http" in sys.argv:
        # HTTP server mode
        idx = sys.argv.index("--http")
        port = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 9876
        import http.server
        from urllib.parse import urlparse

        load_model()
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/health":
                    self._json(200, {"status": "ok", "refs": list(REF_FILES.keys()), "model_loaded": MODEL is not None})
                else:
                    self._json(404, {"error": "not found"})
            def do_POST(self):
                path = urlparse(self.path).path
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body) if body.strip() else {}
                if path == "/clone":
                    text = data.get("text", "").strip()
                    if not text:
                        self._json(400, {"error": "text required"})
                        return
                    result = handle(text, data.get("language", "pt")[:2], data.get("voice", ""))
                    self._json(200, result)
                else:
                    self._json(404, {"error": "not found"})
            def _json(self, code, data):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            def log_message(self, fmt, *a):
                log.info(fmt % a)

        server = http.server.HTTPServer(("127.0.0.1", port), Handler)
        log.info(f"HTTP on :{port}")
        signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
        try: server.serve_forever()
        except KeyboardInterrupt: server.shutdown()
        return

    # Default: stdin/stdout protocol (one request per invocation)
    if os.isatty(sys.stdin.fileno()):
        # Interactive test mode
        load_model()
        log.info("Interactive mode. Send JSON lines via stdin.")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                result = handle(req.get("text", ""), req.get("language", "pt")[:2], req.get("voice", ""))
                print(json.dumps(result), flush=True)
            except Exception as e:
                log.error(f"Error: {e}")
        return

    # Request from pipe
    if MODEL is None:
        load_model()
    try:
        req = json.loads(sys.stdin.read())
        result = handle(req.get("text", ""), req.get("language", "pt")[:2], req.get("voice", ""))
        print(json.dumps(result), flush=True)
    except Exception as e:
        log.error(f"Fatal: {e}\n{traceback.format_exc()}")
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
