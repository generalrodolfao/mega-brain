"""
Persistent Memory — J.A.R.V.I.S. remembers who you are.

Structured JSON memory organized by categories.
Auto-trims to stay within context window limits.
"""

import json
import os
from pathlib import Path
from datetime import datetime

logger = __import__("logging").getLogger("mega-brain")

MEMORY_PATH = Path(__file__).parent.parent / "data" / "memory.json"
MAX_CHARS = 3000

CATEGORIES = [
    "identity",       # nome, profissão, onde mora
    "preferences",    # gostos, estilo de resposta preferido
    "projects",       # projetos ativos, objetivos
    "relationships",  # pessoas importantes, contatos
    "facts",          # fatos aprendidos
    "notes",          # notas soltas
]


def _ensure():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text(json.dumps({c: {} for c in CATEGORIES}, indent=2, ensure_ascii=False))


def load() -> dict:
    _ensure()
    try:
        return json.loads(MEMORY_PATH.read_text())
    except Exception:
        return {c: {} for c in CATEGORIES}


def save(data: dict):
    _ensure()
    MEMORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logger.info(f"  Memória salva ({_count_entries(data)} entradas)")


def _count_entries(data: dict) -> int:
    return sum(len(v) for v in data.values() if isinstance(v, dict))


def update(category: str, key: str, value: str):
    """Store a memory entry under category/key."""
    data = load()
    if category not in data:
        category = "notes"
    if category not in data:
        data[category] = {}
    data[category][key] = {
        "value": value,
        "updated": datetime.now().isoformat(),
    }
    _trim(data)
    save(data)


def remember(key: str, value: str):
    """Convenience: store under 'facts'."""
    update("facts", key, value)


def format_for_prompt(data: dict = None) -> str:
    """Format memory as text block for system prompt injection."""
    if data is None:
        data = load()
    lines = []
    for cat in CATEGORIES:
        entries = data.get(cat, {})
        if not entries:
            continue
        lines.append(f"\n[{cat.upper()}]")
        for k, v in entries.items():
            val = v.get("value", v) if isinstance(v, dict) else v
            if val:
                lines.append(f"  {k}: {val}")
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n  [memory truncated]"
    return text


def _trim(data: dict):
    """Remove oldest entries if over MAX_CHARS."""
    text = format_for_prompt(data)
    if len(text) <= MAX_CHARS:
        return
    # Flatten all entries with timestamps
    all_entries = []
    for cat in CATEGORIES:
        for k, v in data.get(cat, {}).items():
            ts = v.get("updated", "2000-01-01") if isinstance(v, dict) else "2000-01-01"
            all_entries.append((ts, cat, k))
    # Remove oldest
    all_entries.sort(key=lambda x: x[0])
    to_remove = max(1, len(all_entries) // 3)
    for _, cat, key in all_entries[:to_remove]:
        if cat in data and key in data[cat]:
            del data[cat][key]


def clear():
    """Reset all memory."""
    save({c: {} for c in CATEGORIES})


CONVERSATION_PATH = Path(__file__).parent.parent / "data" / "conversation.json"


def add_conversation(user: str, assistant: str, max_pairs: int = 8):
    """Append a conversation turn, keeping only recent pairs."""
    CONVERSATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        conv = json.loads(CONVERSATION_PATH.read_text()) if CONVERSATION_PATH.exists() else []
    except Exception:
        conv = []
    conv.append({"user": user, "assistant": assistant, "time": datetime.now().isoformat()})
    # Keep only recent
    if len(conv) > max_pairs:
        conv = conv[-max_pairs:]
    CONVERSATION_PATH.write_text(json.dumps(conv, indent=2, ensure_ascii=False))


def get_conversation(pairs: int = 6) -> list[str]:
    """Get recent conversation history as formatted lines."""
    try:
        if not CONVERSATION_PATH.exists():
            return []
        conv = json.loads(CONVERSATION_PATH.read_text())[-pairs:]
        lines = []
        for turn in conv:
            lines.append(f"Usuário: {turn['user']}")
            lines.append(f"J.A.R.V.I.S.: {turn['assistant']}")
        return lines
    except Exception:
        return []


def stats() -> dict:
    data = load()
    return {
        "total_entries": _count_entries(data),
        "categories": {
            cat: len(data.get(cat, {})) for cat in CATEGORIES
        },
        "memory_size": len(format_for_prompt(data)),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Memory Stats ===")
    print(json.dumps(stats(), indent=2))
    print("\n=== Current Memory ===")
    print(format_for_prompt())
