import json
import httpx
from config import MODELS, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from state import AgentState
from nodes.tools import TOOLS, execute_tool

SYSTEM_PROMPTS = {
    "fast": "Você é um assistente rápido e direto. Responda em português do Brasil de forma concisa.",
    "standard": "Você é um assistente analítico. Pense passo a passo e responda em português do Brasil.",
    "premium": "Você é um assistente de alto nível. Analise profundamente e responda em português do Brasil.",
}


async def call_openrouter(model: str, messages: list, tools: list | None = None) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2048}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient() as client:
        resp = await client.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    message = choice["message"]

    if message.get("tool_calls"):
        tool_msgs = []
        for tc in message["tool_calls"]:
            result = await execute_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]))
            tool_msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
        return await call_openrouter(model, messages + [message] + tool_msgs, tools)

    return message.get("content", "")


async def respond_fast(state: AgentState) -> dict:
    return await _respond(state, "fast", MODELS["fast"])


async def respond_standard(state: AgentState) -> dict:
    return await _respond(state, "standard", MODELS["standard"])


async def respond_premium(state: AgentState) -> dict:
    return await _respond(state, "premium", MODELS["premium"])


async def _respond(state: AgentState, level: str, model_id: str) -> dict:
    system = {"role": "system", "content": SYSTEM_PROMPTS.get(level, SYSTEM_PROMPTS["fast"])}
    messages = [system]
    for msg in state.get("messages", []):
        if hasattr(msg, "content"):
            messages.append({"role": msg.role if hasattr(msg, "role") else "user", "content": msg.content})
        elif isinstance(msg, dict):
            messages.append(msg)

    response = await call_openrouter(model_id, messages, TOOLS)
    return {"response": response, "model_used": model_id, "route": level}
