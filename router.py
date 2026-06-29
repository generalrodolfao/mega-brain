"""
Router Inteligente — "Mega Brain" em 60 linhas de Python.

O "segredo do Mega Brain" é só roteamento inteligente:
  - Frases normais → modelo barato e rápido
  - Menção a "brain" → modelo intermediário
  - Menção a "mega brain" → topo de linha + squad completo
"""

import re
from enum import Enum


class RouteLevel(Enum):
    ECONOMIC = "gemini-2.5-flash-lite"
    MEDIUM = "gpt-4o"
    PREMIUM = "claude-sonnet-4"


class SentimentLevel(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


def classify_sentiment(text: str) -> SentimentLevel:
    """
    Classifica a complexidade baseado em heurísticas simples.
    Em produção, substituir por classificador BERT fine-tuned.
    """
    complex_keywords = [
        "estratégia", "lançamento", "campanha", "completo",
        "análise", "detalhado", "profundo", "complexo"
    ]
    medium_keywords = [
        "criar", "produzir", "escrever", "desenvolver",
        "planejar", "organizar"
    ]

    text_lower = text.lower()

    score = 0
    for kw in complex_keywords:
        if kw in text_lower:
            score += 2
    for kw in medium_keywords:
        if kw in text_lower:
            score += 1

    if score >= 3:
        return SentimentLevel.COMPLEX
    elif score >= 1:
        return SentimentLevel.MEDIUM
    return SentimentLevel.SIMPLE


def detect_keywords(text: str) -> list[str]:
    """Detecta palavras-chave de ativação."""
    text_lower = text.lower()
    found = []
    if "mega brain" in text_lower:
        found.append("mega_brain")
    if re.search(r'\bbrain\b', text_lower):
        found.append("brain")
    return found


def route(text: str) -> dict:
    """
    Decide o modelo e o squad baseado no texto e sentimento.

    Returns:
        dict com model, squad, level e reasoning
    """
    sentiment = classify_sentiment(text)
    keywords = detect_keywords(text)

    # Lógica de roteamento
    if "mega_brain" in keywords:
        return {
            "model": RouteLevel.PREMIUM.value,
            "squad": "copy-chief",
            "level": "mega_brain",
            "reasoning": (
                "Palavra-chave 'mega brain' detectada. "
                "Roteando para modelo topo de linha com squad completo."
            )
        }

    if "brain" in keywords or sentiment == SentimentLevel.MEDIUM:
        return {
            "model": RouteLevel.MEDIUM.value,
            "squad": None,
            "level": "brain",
            "reasoning": (
                "Palavra-chave 'brain' detectada ou complexidade média. "
                "Roteando para modelo intermediário."
            )
        }

    return {
        "model": RouteLevel.ECONOMIC.value,
        "squad": None,
        "level": "normal",
        "reasoning": (
            "Entrada simples. Roteando para modelo econômico e rápido."
        )
    }


# === Demo ===
if __name__ == "__main__":
    test_cases = [
        "Cria um post pro Instagram sobre o novo produto",
        "Brain, preciso de uma thread técnica sobre IA",
        "Ativa o Mega Brain, quero uma estratégia de lançamento completa",
        "Qual a previsão do tempo hoje?",
    ]

    print("=" * 60)
    print("🧠  MEGA BRAIN ROUTER - DEMO")
    print("=" * 60)
    print()

    for i, text in enumerate(test_cases, 1):
        result = route(text)
        print(f"── Caso {i} {'─' * 40}")
        print(f"  Input:  '{text}'")
        print(f"  Model:  {result['model']}")
        print(f"  Squad:  {result['squad'] or 'Nenhum'}")
        print(f"  Nível:  {result['level']}")
        print(f"  Motivo: {result['reasoning']}")
        print()

    print("=" * 60)
    print("✨  A 'mágica' é arquitetura, não feitiço.")
    print("=" * 60)
