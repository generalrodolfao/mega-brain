"""
Mega Brain Server — J.A.R.V.I.S. web interface.

Serves the HTML dashboard, processes chat/voice commands via
the Mega Brain router, and streams real-time state updates
to connected clients via WebSocket.
"""

import json
import os
import asyncio
import logging
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mega-brain")


class DashboardServer:
    """
    Full J.A.R.V.I.S. interface server.
    Routes: / = HTML, /api/process = chat endpoint, /ws = real-time state
    """

    def __init__(self, host: str = "localhost", port: int = 3001):
        self.host = host
        self.port = port
        self.clients = set()
        self.state_path = Path("state.json")
        self._state = {}

    async def broadcast_state(self):
        """Send current state to all connected clients."""
        if not self.state_path.exists():
            return

        state = self.state_path.read_text()
        dead = set()

        for ws in self.clients:
            try:
                await ws.send_text(state)
            except Exception:
                dead.add(ws)

        self.clients -= dead

    async def handle_client(self, websocket):
        """Handle a new WebSocket connection."""
        self.clients.add(websocket)
        logger.info(f"Cliente conectado ({len(self.clients)} total)")

        try:
            async for _ in websocket:
                await self.broadcast_state()
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"Cliente desconectado ({len(self.clients)} total)")

    async def watch_state_file(self):
        """Poll state.json for changes and broadcast."""
        last_mtime = 0

        while True:
            if self.state_path.exists():
                mtime = self.state_path.stat().st_mtime
                if mtime > last_mtime and self.clients:
                    await self.broadcast_state()
                    last_mtime = mtime
            await asyncio.sleep(0.5)

    async def start(self):
        """Start both HTTP server and state file watcher."""
        import aiohttp
        from aiohttp import web

        # Load .env if present
        try:
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        except Exception:
            pass

        # Pre-load Whisper STT model on startup
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.voice import get_whisper_model
            get_whisper_model("tiny")
            logger.info("Modelo STT Whisper carregado")
        except Exception as e:
            logger.warning(f"Falha ao pré-carregar STT: {e}")

        # Start voice clone server in background
        vc_script = Path(__file__).parent / "voice_clone_server.py"
        vc_venv = "/tmp/coqui-venv/bin/python3"
        if vc_script.exists() and Path(vc_venv).exists():
            try:
                import subprocess
                self._vc_proc = subprocess.Popen(
                    [vc_venv, str(vc_script), "--http", "9876"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Servidor de clone de voz iniciando (background)...")
            except Exception as e:
                logger.warning(f"Não foi possível iniciar clone de voz: {e}")
                self._vc_proc = None
        else:
            self._vc_proc = None

        dashboard_path = Path(__file__).parent.parent / "dashboard"

        async def handle_intro(request):
            """Stream tech intro audio (British J.A.R.V.I.S. voice)."""
            import edge_tts, io
            text = "J.A.R.V.I.S. online. Mega Brain system activated. All systems nominal."
            communicate = edge_tts.Communicate(text, "en-GB-RyanNeural", rate="-10%", pitch="-8Hz", volume="+0%")
            async def audio_stream():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]
            resp = web.StreamResponse(status=200, reason="OK", headers={"Content-Type": "audio/mpeg", "Cache-Control": "public, max-age=86400", "X-Accel-Buffering": "no"})
            await resp.prepare(request)
            async for chunk in audio_stream():
                try: await resp.write(chunk)
                except (ConnectionResetError, ConnectionAbortedError): break
            await resp.write_eof()
            return resp

        async def handle_index(request):
            index_file = dashboard_path / "index.html"
            if index_file.exists():
                return web.Response(
                    text=index_file.read_text(),
                    content_type="text/html",
                )
            return web.Response(text="J.A.R.V.I.S. not found", status=404)

        async def handle_voice_status(request):
            """Check voice clone server availability."""
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.voice_clone import is_available, health
            avail = is_available()
            info = health() if avail else {}
            return web.json_response({
                "clone_available": avail,
                "clone_info": info,
                "edge_tts": True,
            })

        async def handle_config(request):
            """GET: return current config (masked). POST: update API keys."""
            if request.method == "GET":
                key = os.getenv("OPENROUTER_API_KEY") or ""
                masked = key[:8] + "..." + key[-4:] if len(key) > 12 else ""
                return web.json_response({
                    "openrouter_key": masked,
                    "has_key": bool(key),
                    "whisper_model": "tiny",
                    "tts_voice": "en-GB-RyanNeural",
                })
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)
            key = (data.get("openrouter_key") or "").strip()
            if key:
                os.environ["OPENROUTER_API_KEY"] = key
                logger.info("Chave OpenRouter atualizada")
                return web.json_response({"ok": True})
            return web.json_response({"error": "key required"}, status=400)

        async def handle_memory(request):
            """GET: return conversation history and memory stats."""
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.memory import stats, format_for_prompt, get_conversation
            return web.json_response({
                "stats": stats(),
                "memory": format_for_prompt(),
                "conversation": get_conversation(12),
            })

        async def handle_upload(request):
            """Upload a file for the model to analyze."""
            try:
                reader = await request.multipart()
                field = await reader.next()
                if not field or not field.filename:
                    return web.json_response({"error": "file required"}, status=400)
                data = await field.read()
                filename = field.filename
                ext = Path(filename).suffix.lower()
                # Save to temp
                temp = Path(f"/tmp/mb_upload_{uuid.uuid4().hex[:8]}{ext}")
                temp.write_bytes(data)
                # Read content based on type
                text = ""
                if ext in (".txt", ".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".yaml", ".yml", ".csv"):
                    text = data.decode("utf-8", errors="replace")[:8000]
                elif ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    text = f"[Imagem: {filename} ({len(data)} bytes)]"
                    # For image analysis, pass the base64 to the model
                    import base64
                    b64 = base64.b64encode(data).decode()
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext.replace(".", ""), "image/png")
                    text = f"[Imagem: {filename}]\n![{filename}](data:{mime};base64,{b64})"
                elif ext == ".pdf":
                    try:
                        import PyPDF2
                        with open(temp, "rb") as f:
                            reader_pdf = PyPDF2.PdfReader(f)
                            text = "\n".join(p.extract_text() for p in reader_pdf.pages[:10])[:8000]
                    except ImportError:
                        text = f"[PDF não processado: pip install PyPDF2]"
                elif ext in (".mp3", ".wav", ".ogg", ".m4a", ".webm"):
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    from core.voice import VoiceInput
                    stt = VoiceInput()
                    text = stt.transcribe_file(str(temp), language="pt")
                temp.unlink(missing_ok=True)
                return web.json_response({"filename": filename, "text": text.strip(), "size": len(data)})
            except Exception as e:
                logger.error(f"Erro no upload: {e}")
                return web.json_response({"error": str(e)}, status=500)

        async def handle_squad(request):
            """Run multi-agent squad: parallel agents + consolidation."""
            import time as tm
            t0 = tm.time()
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)
            text = (data.get("text") or "").strip()
            if not text:
                return web.json_response({"error": "text required"}, status=400)

            import sys, asyncio
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.openrouter import OpenRouterClient
            from core.router import route

            decision = route(text)
            client = OpenRouterClient()

            # Agent definitions — sub-agents ativados no modo overdrive
            mode = data.get("mode", "normal")
            agents = {
                "strategist": {"role": "Estrategista de marketing e produto", "prompt": "Você é um estrategista sênior. Analise o briefing e produza um plano estratégico com: objetivos, público-alvo, canais, KPIs. Seja conciso."},
                "copywriter": {"role": "Copywriter sênior", "prompt": "Você é um copywriter sênior. Crie copies persuasivas: headline, subheadline, CTA, e 3 variações de chamada para ação."},
                "designer": {"role": "Diretor de arte", "prompt": "Você é um diretor de arte. Descreva o conceito visual: paleta de cores, tipografia, estilo de imagens, layout. Seja específico."},
                "seo": {"role": "Especialista SEO", "prompt": "Você é um especialista SEO. Analise e recomende: palavras-chave principais, estrutura de conteúdo, meta tags, estratégia de links."},
                "reviewer": {"role": "Revisor de qualidade", "prompt": "Você é um revisor. Analise criticamente todo o plano e aponte: riscos, gaps, inconsistências, melhorias sugeridas."},
            }
            # Sub-agents: ativados no modo overdrive
            if mode == "overdrive":
                sub_agents = {
                    "data-analyst": {"role": "Analista de dados", "prompt": "Você é um analista de dados. Forneça métricas, benchmarks e dados de mercado relevantes para embasar as decisões estratégicas."},
                    "editor": {"role": "Editor de conteúdo", "prompt": "Você é um editor. Revise e refine o copy: tom de voz, clareza, gramática, consistência de marca."},
                    "illustrator": {"role": "Ilustrador conceptual", "prompt": "Você é um ilustrador. Descreva visuais específicos: moodboard, referências visuais, paleta estendida, texturas."},
                    "analytics": {"role": "Analista de métricas", "prompt": "Você é um analista de métricas. Defina KPIs específicos, metas numéricas, ferramentas de mensuração e relatórios."},
                    "qa-tester": {"role": "QA Tester", "prompt": "Você é um QA tester. Teste o plano: identifique falhas lógicas, contradições, riscos operacionais e gaps de execução."},
                }
                agents.update(sub_agents)

            async def run_agent(name, cfg):
                try:
                    r = client.chat("gpt-4o", [
                        {"role": "user", "content": f"Briefing: {text}\n\nSeu papel: {cfg['role']}\n\n{cfg['prompt']}"}
                    ], temperature=0.7, max_tokens=1024)
                    return name, r.get("content", ""), r.get("usage", {}).get("total_tokens", 0)
                except Exception as e:
                    return name, f"Erro: {e}", 0

            # Run agents in parallel
            results = await asyncio.gather(*[run_agent(n, c) for n, c in agents.items()])

            # Consolidate
            outputs = {n: c for n, c, _ in results}
            total_tokens = sum(t for _, _, t in results)

            consolidation = client.chat("claude-sonnet-4", [
                {"role": "user", "content": f"Consolide estas análises de agentes em um plano coeso e executável:\n\nEstrategista:\n{outputs.get('strategist', '')}\n\nCopywriter:\n{outputs.get('copywriter', '')}\n\nDesigner:\n{outputs.get('designer', '')}\n\nSEO:\n{outputs.get('seo', '')}\n\nRevisor:\n{outputs.get('reviewer', '')}"}
            ], system_prompt="Você é um diretor de criação. Consolide em um plano único, coeso, hierárquico. Seção obrigatória: PRÓXIMOS PASSOS.", temperature=0.5, max_tokens=2048)

            elapsed = tm.time() - t0
            logger.info(f"Esquadrão: {elapsed:.1f}s, {total_tokens} tok")
            return web.json_response({
                "session": "SQ-" + uuid.uuid4().hex[:6].upper(),
                "input": text,
                "outputs": outputs,
                "consolidated": consolidation.get("content", ""),
                "total_tokens": total_tokens,
                "elapsed": round(elapsed, 1),
            })

        async def handle_research(request):
            """Deep Research: search web, analyze, consolidate."""
            import time as tm
            t0 = tm.time()
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)
            query = (data.get("query") or "").strip()
            if not query:
                return web.json_response({"error": "query required"}, status=400)

            import sys, asyncio, httpx
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.openrouter import OpenRouterClient

            client = OpenRouterClient()

            # Parallel searches
            async def search(q):
                try:
                    r = await asyncio.to_thread(lambda: httpx.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1}, timeout=10))
                    d = r.json()
                    return d.get("AbstractText", "") or (d.get("RelatedTopics", [{}])[0].get("Text", "") if d.get("RelatedTopics") else "")
                except Exception:
                    return ""

            queries = [query, f"{query} 2026 tendências", f"{query} análise"]
            search_results = await asyncio.gather(*[search(q) for q in queries])
            context = "\n\n".join(f"**Fonte {i+1}:** {s}" for i, s in enumerate(search_results) if s)

            # Analyze with o3-mini
            result = client.chat("o3-mini", [
                {"role": "user", "content": f"Pergunta: {query}\n\nResultados de busca:\n{context or 'Nenhum resultado encontrado.'}\n\nFaça uma análise profunda: sumarize as descobertas, identifique tendências, contradições, e forneça conclusões acionáveis. Formato: ## Resumo, ## Análise, ## Tendências, ## Conclusões."}
            ], system_prompt="Você é um analista de pesquisa sênior. Seja objetivo, baseado em dados.", temperature=0.3, max_tokens=2048)

            elapsed = tm.time() - t0
            logger.info(f"Pesquisa: {elapsed:.1f}s")
            return web.json_response({
                "session": "RS-" + uuid.uuid4().hex[:6].upper(),
                "query": query,
                "sources": search_results,
                "analysis": result.get("content", ""),
                "model": result.get("model", ""),
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "elapsed": round(elapsed, 1),
            })

        async def handle_stt(request):
            """Transcribe audio using Whisper (local)."""
            import time as time_mod
            t0 = time_mod.time()
            try:
                reader = await request.multipart()
                field = await reader.next()
                if not field or not field.filename:
                    return web.json_response({"error": "audio file required"}, status=400)

                audio_data = await field.read()
                temp_path = Path("/tmp/mega_brain_stt_input.wav")
                temp_path.write_bytes(audio_data)

                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from core.voice import VoiceInput

                stt = VoiceInput(model_size="tiny")
                text = stt.transcribe_file(str(temp_path), language="pt")
                temp_path.unlink(missing_ok=True)

                elapsed = time_mod.time() - t0
                logger.info(f"STT: '{text[:40]}...' in {elapsed:.1f}s")
                return web.json_response({"text": text.strip()})
            except Exception as e:
                elapsed = time_mod.time() - t0
                logger.error(f"Erro STT após {elapsed:.1f}s: {e}")
                return web.json_response({"error": str(e)}, status=500)

        async def handle_image(request):
            """Generate an image via OpenRouter."""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)
            prompt = (data.get("prompt") or "").strip()
            if not prompt:
                return web.json_response({"error": "prompt required"}, status=400)

            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.openrouter import OpenRouterClient

            client = OpenRouterClient()
            result = client.chat("gpt-4o", [
                {"role": "user", "content": f"Generate a detailed image prompt for: {prompt}"}
            ], system_prompt="You are an expert image prompt engineer. Return ONLY a detailed, visual prompt in English for an AI image generator.")
            if result.get("error"):
                return web.json_response({"error": result["content"]}, status=500)

            return web.json_response({
                "image_url": result.get("content", ""),
                "alt": prompt,
                "model": result.get("model", ""),
                "session": "IMG-" + uuid.uuid4().hex[:6].upper(),
            })

        async def handle_state(request):
            return web.json_response(self._state)

        async def handle_process(request):
            """Process a chat command through the Mega Brain router."""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)

            text = (data.get("text") or "").strip()
            if not text:
                return web.json_response({"error": "text required"}, status=400)

            # Import modules
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.router import route
            from core.openrouter import OpenRouterClient

            decision = route(text)
            session_id = "MB-" + uuid.uuid4().hex[:6].upper()

            # Call the actual model via OpenRouter
            client = OpenRouterClient()
            model_result = client.route_and_chat(text, {
                "model": decision.model,
                "level": decision.level,
                "squad": decision.squad,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
            })

            sa = decision.sentiment_analysis
            result = {
                "session": session_id,
                "input": text,
                "level": decision.level,
                "model": model_result.get("model", decision.model),
                "mode": getattr(decision, "mode", "normal"),
                "squad": decision.squad,
                "complexity": decision.complexity.value,
                "sentiment": decision.sentiment,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "response": model_result.get("content", ""),
                "usage": model_result.get("usage", {}),
                "finish_reason": model_result.get("finish_reason", ""),
                "error": model_result.get("error", False),
                "satisfaction": sa.satisfaction if sa else "neutro",
                "tone": sa.tone if sa else "neutro",
                "emotion": sa.emotion if sa else "indiferença",
                "sentiment_source": sa.source if sa else "keyword",
            }

            # Update internal state & broadcast
            status = "error" if result.get("error") else ("active" if decision.squad else "idle")
            sa = decision.sentiment_analysis
            self._state = {
                "session": session_id,
                "level": decision.level,
                "model": result["model"],
                "squad": decision.squad,
                "input": text,
                "status": status,
                "satisfaction": sa.satisfaction if sa else "neutro",
                "tone": sa.tone if sa else "neutro",
                "emotion": sa.emotion if sa else "indiferença",
            }
            await self.broadcast_state()

            tokens = result.get("usage", {}).get("total_tokens", 0)
            logger.info(f"[{session_id}] {decision.level} -> {result['model']} ({tokens} tok) | '{text[:60]}'")

            # Save conversation turn
            try:
                from core.memory import add_conversation
                add_conversation(text, result.get("response", ""))
            except Exception:
                pass

            return web.json_response(result)

        async def handle_tts(request):
            """Stream edge-tts audio directly, no delays."""
            import time as time_mod
            t0 = time_mod.time()
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "invalid JSON"}, status=400)

            text = (data.get("text") or "").strip()
            language = data.get("language", "pt-BR")
            if not text:
                return web.json_response({"error": "text required"}, status=400)

            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))

            import io, edge_tts
            voice_map = {"pt-BR": "pt-BR-AntonioNeural", "en": "en-GB-RyanNeural"}
            voice = voice_map.get(language, "en-GB-RyanNeural")

            communicate = edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz", volume="+0%")

            # Stream audio as it's generated
            async def audio_stream():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]

            logger.info(f"TTS transmitindo: '{text[:40]}...' prep={time_mod.time()-t0:.2f}s")
            resp = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "audio/mpeg",
                    "Cache-Control": "public, max-age=86400",
                    "X-Accel-Buffering": "no",
                },
            )
            await resp.prepare(request)
            async for chunk in audio_stream():
                try:
                    await resp.write(chunk)
                except (ConnectionResetError, ConnectionAbortedError):
                    break
            await resp.write_eof()
            return resp

        async def websocket_handler(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await self.handle_client(ws)
            return ws

        app = web.Application()
        app.router.add_get("/", handle_index)
        app.router.add_get("/state.json", handle_state)
        app.router.add_get("/api/voice-clone/status", handle_voice_status)
        app.router.add_get("/api/config", handle_config)
        app.router.add_post("/api/config", handle_config)
        app.router.add_get("/api/memory", handle_memory)
        app.router.add_post("/api/upload", handle_upload)
        app.router.add_post("/api/squad", handle_squad)
        app.router.add_post("/api/research", handle_research)
        app.router.add_post("/api/process", handle_process)
        app.router.add_post("/api/stt", handle_stt)
        app.router.add_post("/api/tts", handle_tts)
        app.router.add_post("/api/image", handle_image)
        app.router.add_get("/api/intro", handle_intro)
        app.router.add_get("/ws", websocket_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Painel Mega Brain: http://{self.host}:{self.port}")
        await self.watch_state_file()


def run_server(host: str = "localhost", port: int = 3001):
    """Convenience function to run the dashboard server."""
    server = DashboardServer(host, port)
    asyncio.run(server.start())


if __name__ == "__main__":
    run_server()
