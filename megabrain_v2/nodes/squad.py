import httpx
import asyncio
from config import SQUAD_AGENTS, MODELS, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from state import AgentState


async def call_openrouter(messages: list, model: str) -> str:
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 1024}

    async with httpx.AsyncClient() as client:
        resp = await client.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def squad_fanout(state: AgentState) -> dict:
    task = state["messages"][-1].content if state["messages"] else ""

    agents_to_run = list(SQUAD_AGENTS.items())[:4]

    async def run_one(name, cfg):
        messages = [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": f"TAREFA: {task}\n\nExecute sua parte e retorne o resultado."},
        ]
        result = await call_openrouter(messages, cfg["model"])
        return {"agent": name, "result": result}

    results = await asyncio.gather(*[run_one(n, c) for n, c in agents_to_run])

    return {
        "squad_results": results,
        "squad_status": "agents_done",
    }


async def squad_consolidate(state: AgentState) -> dict:
    results = state.get("squad_results", [])
    if not results:
        return {"response": "Nenhum resultado dos agentes.", "model_used": MODELS["squad_chief"]}

    combined = "\n\n---\n\n".join(f"## {r['agent'].upper()}\n{r['result']}" for r in results)

    messages = [
        {
            "role": "system",
            "content": (
                "Você é o Copy Chief do Mega Brain. Consolide o trabalho dos agentes "
                "em uma resposta final coesa. Responda em português do Brasil."
            ),
        },
        {"role": "user", "content": f"Consolide em uma resposta final:\n\n{combined}"},
    ]

    final = await call_openrouter(messages, MODELS["squad_chief"])

    return {"response": final, "model_used": MODELS["squad_chief"]}
