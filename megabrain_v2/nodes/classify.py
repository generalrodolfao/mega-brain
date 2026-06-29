import re
from config import ROUTE_KEYWORDS
from state import AgentState


def analyze_sentiment(state: AgentState) -> dict:
    if not state["messages"]:
        return {"sentiment": "neutro"}

    content = _get_text(state)
    positivo = ["obrigado", "valeu", "top", "incrível", "show", "👍", "amei"]
    negativo = ["ruim", "péssimo", "odeio", "lixo", "😡", "não gostei"]

    if any(p in content for p in positivo):
        return {"sentiment": "positivo"}
    if any(n in content for n in negativo):
        return {"sentiment": "negativo"}
    return {"sentiment": "neutro"}


def detect_complexity(state: AgentState) -> dict:
    content = _get_text(state)
    words = len(content.split())
    questions = len(re.findall(r"\?", content))
    has_code = bool(re.search(r"```|def |function|import |class ", content))

    if has_code:
        return {"complexity": "high"}
    if words > 300:
        return {"complexity": "high"}
    if words > 120 or questions >= 3:
        return {"complexity": "medium"}
    return {"complexity": "low"}


def decide_route(state: AgentState) -> dict:
    content = _get_text(state)

    for route, keywords in ROUTE_KEYWORDS.items():
        if any(kw.lower() in content for kw in keywords):
            return {"route": route}

    complexity = state.get("complexity", "low")
    if complexity == "high":
        return {"route": "premium"}
    if complexity == "medium":
        return {"route": "standard"}
    return {"route": "fast"}


def _get_text(state: AgentState) -> str:
    if not state["messages"]:
        return ""
    last = state["messages"][-1]
    return (last.content if hasattr(last, "content") else str(last)).lower()
