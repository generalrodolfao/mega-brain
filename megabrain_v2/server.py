import asyncio
import json
import uuid
import aiohttp
from aiohttp import web

from graph import build_graph
from langchain_core.messages import HumanMessage

app_graph = build_graph()
connected_clients = set()
routes = web.RouteTableDef()


@routes.get("/")
async def index(request):
    return web.FileResponse("demo.html")


@routes.get("/grafo")
async def grafo(request):
    return web.FileResponse("grafo.html")


@routes.get("/demo")
async def demo(request):
    return web.FileResponse("demo.html")


@routes.get("/state.json")
async def get_state(request):
    return web.json_response({
        "system": "Mega Brain v2",
        "version": "2.0.0",
        "status": "online",
        "engine": "LangGraph",
    })


@routes.post("/api/process")
async def handle_process(request):
    data = await request.json()
    text = data.get("text", "")
    thread_id = data.get("thread_id", str(uuid.uuid4()))

    config = {"configurable": {"thread_id": thread_id}}

    result_state = None
    async for event in app_graph.astream(
        {"messages": [HumanMessage(content=text)]},
        config,
        stream_mode="values",
    ):
        result_state = event

    response = {
        "thread_id": thread_id,
        "response": result_state.get("response", "") if result_state else "",
        "route": result_state.get("route", "fast") if result_state else "fast",
        "model_used": result_state.get("model_used", "") if result_state else "",
        "squad_results": result_state.get("squad_results", []) if result_state else [],
    }

    for ws in connected_clients:
        try:
            await ws.send_json(response)
        except Exception:
            pass

    return web.json_response(response)


@routes.get("/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
    finally:
        connected_clients.discard(ws)

    return ws


async def main():
    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8701)
    await site.start()

    print("Mega Brain v2 (LangGraph) — http://localhost:8701")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
