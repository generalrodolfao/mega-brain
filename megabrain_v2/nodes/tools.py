import json
import math
import httpx
from datetime import datetime

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Retorna a data e hora atual no formato ISO 8601.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Avalia uma expressão matemática e retorna o resultado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expressão matemática para avaliar (ex: '2 + 2 * 3')."
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca informações na web via DuckDuckGo Instant Answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca."
                    }
                },
                "required": ["query"],
            },
        },
    },
]

SAFE_BUILTINS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
}


async def execute_tool(name: str, args: dict) -> str:
    if name == "get_time":
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    elif name == "calculate":
        expression = args.get("expression", "")
        allowed = SAFE_BUILTINS.copy()
        allowed["__builtins__"] = {}
        try:
            result = eval(expression, {"__builtins__": {}}, allowed)
            return str(result)
        except Exception as e:
            return f"Erro no cálculo: {e}"

    elif name == "web_search":
        query = args.get("query", "")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1},
                    timeout=10,
                )
                data = resp.json()
                abstract = data.get("AbstractText", "")
                if abstract:
                    return abstract
                related = data.get("RelatedTopics", [])
                if related:
                    return related[0].get("Text", "Sem resultados.")
                return "Nenhum resultado encontrado."
        except Exception as e:
            return f"Erro na busca: {e}"

    return f"Ferramenta '{name}' não encontrada."
