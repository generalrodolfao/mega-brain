"""
Tool definitions for J.A.R.V.I.S. function calling.

Declares tools in OpenAI-compatible format (works with OpenRouter)
and dispatches execution to local functions.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("mega-brain")

# === TOOL DECLARATIONS (OpenAI/OpenRouter format) ===
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save information about the user (identity, preferences, projects, facts). Call this SILENTLY whenever you learn something personal. Do NOT announce it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["identity", "preferences", "projects", "relationships", "facts", "notes"],
                        "description": "Category of memory"
                    },
                    "key": {
                        "type": "string",
                        "description": "Memory key (e.g. 'nome', 'profissao', 'projeto_atual')"
                    },
                    "value": {
                        "type": "string",
                        "description": "The value to remember"
                    }
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_memory",
            "description": "Retrieve stored memories. Use to recall user information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "identity", "preferences", "projects", "relationships", "facts", "notes"],
                        "description": "Category to retrieve, or 'all'"
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use when you need up-to-date data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression (e.g. '2 + 2', 'sqrt(144)')"
                    }
                },
                "required": ["expression"]
            }
        }
    },
]


def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool by name with given arguments. Returns result text."""
    logger.info(f"  Chamada de ferramenta: {tool_name}({arguments})")

    try:
        if tool_name == "save_memory":
            from core.memory import update
            update(arguments["category"], arguments["key"], arguments["value"])
            return json.dumps({"result": "ok", "silent": True})

        elif tool_name == "get_memory":
            from core.memory import load, format_for_prompt, CATEGORIES
            data = load()
            cat = arguments.get("category", "all")
            if cat == "all":
                return format_for_prompt(data)
            elif cat in data:
                entries = data[cat]
                if entries:
                    lines = [f"[{cat.upper()}]"]
                    for k, v in entries.items():
                        val = v.get("value", v) if isinstance(v, dict) else v
                        lines.append(f"  {k}: {val}")
                    return "\n".join(lines)
                else:
                    return f"Nenhuma informação em {cat}."
            else:
                return f"Categoria '{cat}' não encontrada."

        elif tool_name == "get_time":
            now = datetime.now()
            return json.dumps({
                "datetime": now.isoformat(),
                "date": now.strftime("%d/%m/%Y"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": now.strftime("%A"),
            }, ensure_ascii=False)

        elif tool_name == "web_search":
            try:
                import httpx
                query = arguments.get("query", "")
                r = httpx.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    timeout=10,
                )
                data = r.json()
                abstract = data.get("AbstractText", "")
                source = data.get("AbstractSource", "")
                url = data.get("AbstractURL", "")
                if abstract:
                    return f"{abstract}\nFonte: {source}\nURL: {url}"
                # Fallback: related topics
                topics = data.get("RelatedTopics", [])
                if topics:
                    results = []
                    for t in topics[:5]:
                        if "Text" in t:
                            results.append(t["Text"])
                    return "\n".join(results) if results else "Nenhum resultado encontrado."
                return "Nenhum resultado encontrado."
            except Exception as e:
                return f"Erro na busca: {e}"

        elif tool_name == "calculate":
            expr = arguments.get("expression", "")
            # Safe eval with only math operations
            import math
            allowed = {"abs": abs, "round": round, "int": int, "float": float,
                       "str": str, "len": len, "range": range, "min": min,
                       "max": max, "sum": sum, "pow": pow, "sqrt": math.sqrt}
            try:
                result = eval(expr, {"__builtins__": {}}, allowed)
                return json.dumps({"expression": expr, "result": str(result)})
            except Exception as e:
                return json.dumps({"error": str(e)})

        else:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})

    except Exception as e:
        logger.error(f"  Erro na execução da ferramenta: {e}")
        return json.dumps({"error": str(e)})


def process_tool_calls(response_choices: list) -> list[dict]:
    """Process tool calls from model response.
    
    Returns list of tool response messages to append.
    """
    tool_results = []
    for choice in response_choices:
        msg = choice.get("message", {})
        if "tool_calls" not in msg:
            continue
        for tc in msg["tool_calls"]:
            func = tc.get("function", {})
            name = func.get("name", "")
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            result = execute_tool(name, args)
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "name": name,
                "content": result,
            })
    return tool_results
