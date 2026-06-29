"""
Mega Brain Router — Sentiment Analysis + Model Routing.

The "secret" of the Mega Brain: intelligent routing based on
input complexity, keywords, and sentiment. Routes to different
models and activates different squads based on the detected level.

Includes LLM-based sentiment analysis for understanding user
satisfaction, tone, and emotional state — not just keywords.
"""

import json
import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("mega-brain")


class RouteLevel(Enum):
    ECONOMIC = "gemini-2.5-flash-lite"
    MEDIUM = "gpt-4o"
    PREMIUM = "claude-sonnet-4"
    ULTRA = "o3"
    OVERDRIVE = "claude-sonnet-4"


class Complexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class SentimentAnalysis:
    satisfaction: str  # "satisfeito" | "neutro" | "insatisfeito"
    tone: str          # "positivo" | "neutro" | "negativo" | "urgente"
    emotion: str       # e.g. "curiosidade", "frustração", "entusiasmo", "indiferença"
    reasoning: str
    source: str = "keyword"  # "keyword" | "llm"


@dataclass
class RouteDecision:
    model: str
    squad: Optional[str]
    level: str
    complexity: Complexity
    sentiment: str
    sentiment_analysis: Optional[SentimentAnalysis] = None
    keywords_found: list[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 1.0
    mode: str = "normal"  # "normal" | "overdrive"


# Hierarchical keyword system
KEYWORDS = {
    "overdrive": {
        "terms": [
            "200%", "overdrive", "modo overdrive", "full power", "poder máximo",
            "power max", "força total", "potência máxima", "cem porcento",
            "100%", "todos agentes", "sub agentes",
        ],
        "level": RouteLevel.OVERDRIVE,
        "squad": "copy-chief",
    },
    "ultra": {
        "terms": [
            "mega brain", "megabrain", "mega-brain", "modo deus", "modo supremo",
            "sistema completo", "orquestração total", "deep research",
            "modo avançado", "ativar completo", "cérebro total",
            "inteligência máxima", "poder total",
        ],
        "level": RouteLevel.ULTRA,
        "squad": "copy-chief",
    },
    "premium": {
        "terms": [
            "estratégia completa", "análise profunda", "projeto complexo",
        ],
        "level": RouteLevel.PREMIUM,
        "squad": "copy-chief",
    },
    "medium": {
        "terms": [
            "brain", "cérebro", "análise", "estratégia",
            "planejar", "desenvolver", "criar campanha",
            "produzir conteúdo", "escrever artigo",
        ],
        "level": RouteLevel.MEDIUM,
        "squad": None,
    },
}

COMPLEXITY_PATTERNS = {
    Complexity.SIMPLE: {
        "patterns": [
            r"^(qual|o que|quem|quando|onde)\s",
            r"^(me diga|fale|conte|explique)\s",
            r"^(bom dia|boa tarde|boa noite|oi|olá)",
            r".{0,50}$",
        ],
        "min_keywords": 0,
    },
    Complexity.MEDIUM: {
        "patterns": [
            r"^(crie|faça|produza|gere|monte)",
            r"^(preciso de|quero|gostaria)",
            r"^(me ajude|me ajuda|pode criar)",
        ],
        "min_keywords": 1,
    },
    Complexity.COMPLEX: {
        "patterns": [
            r"^(crie um sistema|desenvolva|estruture|arquitete)",
            r"^(análise completa|estudo|pesquisa)",
        ],
        "min_keywords": 2,
    },
    Complexity.EXPERT: {
        "patterns": [
            r"^(mega brain|ativar|modo expert|deep dive)",
        ],
        "min_keywords": 3,
    },
}


def analyze_sentiment(text: str) -> str:
    """Simple sentiment analysis based on tone markers."""
    text_lower = text.lower()
    positive = ["obrigado", "por favor", "ajuda", "preciso"]
    urgent = ["urgente", "rápido", "agora", "imediato", "corre"]
    
    if any(w in text_lower for w in urgent):
        return "urgent"
    if any(w in text_lower for w in positive):
        return "positive"
    return "neutral"


def analyze_sentiment_llm(text: str) -> Optional[SentimentAnalysis]:
    """
    LLM-based sentiment analysis using OpenRouter (fast/cheap model).
    Detects satisfaction level, tone, and emotion from natural language.

    Returns SentimentAnalysis or None if LLM call fails (falls back to keyword).
    """
    try:
        from core.openrouter import OpenRouterClient

        client = OpenRouterClient()
        prompt = (
            "Analise o sentimento do texto abaixo. "
            "Responda APENAS um JSON com estes campos:\n"
            '  - "satisfaction": "satisfeito" | "neutro" | "insatisfeito"\n'
            '  - "tone": "positivo" | "neutro" | "negativo" | "urgente"\n'
            '  - "emotion": uma palavra descrevendo a emoção dominante (ex: curiosidade, frustração, entusiasmo, indiferença, admiração, irritação)\n'
            '  - "reasoning": curta explicação em português\n\n'
            f"Texto: {text}"
        )
        result = client.chat(
            model_alias="gemini-2.5-flash-lite",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        content = result.get("content", "").strip()
        content_clean = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        data = json.loads(content_clean)
        return SentimentAnalysis(
            satisfaction=data.get("satisfaction", "neutro"),
            tone=data.get("tone", "neutro"),
            emotion=data.get("emotion", "indiferença"),
            reasoning=data.get("reasoning", "Análise via LLM."),
            source="llm",
        )
    except Exception as e:
        logger.debug(f"LLM sentiment analysis failed, using keyword fallback: {e}")
        return None


def detect_keywords(text: str) -> list[tuple[str, str]]:
    """Detect hierarchical keywords in text."""
    text_lower = text.lower()
    found = []

    for level_name, level_data in KEYWORDS.items():
        for term in level_data["terms"]:
            if term in text_lower:
                found.append((term, level_name))

    found.sort(key=lambda x: list(KEYWORDS.keys()).index(x[1]) if x[1] in KEYWORDS else 99)
    return found


def classify_complexity(text: str) -> Complexity:
    """Classify input complexity based on patterns and length."""
    text_lower = text.lower()
    
    for complexity in [Complexity.EXPERT, Complexity.COMPLEX, Complexity.MEDIUM]:
        config = COMPLEXITY_PATTERNS[complexity]
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                return complexity

    word_count = len(text.split())
    if word_count > 50:
        return Complexity.COMPLEX
    elif word_count > 15:
        return Complexity.MEDIUM
    
    return Complexity.SIMPLE


def route(input_text: str) -> RouteDecision:
    """
    Full routing pipeline:
    1. Detect keywords → highest wins
    2. Classify complexity as fallback
    3. LLM sentiment analysis (satisfaction, tone, emotion)
    4. Determine model, squad, and level
    5. Return structured decision with full sentiment context
    """
    sentiment = analyze_sentiment(input_text)
    keywords = detect_keywords(input_text)
    complexity = classify_complexity(input_text)

    sentiment_llm = analyze_sentiment_llm(input_text)
    sentiment_analysis = sentiment_llm or SentimentAnalysis(
        satisfaction="neutro",
        tone=sentiment,
        emotion="indiferença",
        reasoning="Análise baseada em palavras-chave.",
        source="keyword",
    )

    # Priority 1: Explicit keyword match
    if keywords:
        top_term, top_level_name = keywords[0]
        top_level = KEYWORDS[top_level_name]
        return RouteDecision(
            model=top_level["level"].value,
            squad=top_level["squad"],
            level=top_level_name,
            complexity=complexity,
            sentiment=sentiment,
            sentiment_analysis=sentiment_analysis,
            keywords_found=[k[0] for k in keywords],
            reasoning=f"Palavra-chave '{top_term}' detectada (nível {top_level_name}).",
            confidence=0.95,
            mode="overdrive" if top_level_name == "overdrive" else "normal",
        )

    # Priority 2: Complexity-based routing
    complexity_map = {
        Complexity.SIMPLE: (RouteLevel.ECONOMIC, None, "normal"),
        Complexity.MEDIUM: (RouteLevel.MEDIUM, None, "brain"),
        Complexity.COMPLEX: (RouteLevel.PREMIUM, "copy-chief", "mega_brain"),
        Complexity.EXPERT: (RouteLevel.ULTRA, "copy-chief", "ultra"),
    }

    model, squad, level = complexity_map[complexity]
    
    reasoning_map = {
        Complexity.SIMPLE: "Entrada simples e curta. Roteando para modelo econômico.",
        Complexity.MEDIUM: "Complexidade média detectada. Roteando para modelo intermediário.",
        Complexity.COMPLEX: "Entrada complexa detectada. Roteando para modelo premium com squad.",
        Complexity.EXPERT: "Modo expert ativado. Roteando para ultra com squad completo.",
    }

    return RouteDecision(
        model=model.value,
        squad=squad,
        level=level,
        complexity=complexity,
        sentiment=sentiment,
        sentiment_analysis=sentiment_analysis,
        keywords_found=[],
        reasoning=reasoning_map[complexity],
        confidence=0.85 if complexity in [Complexity.COMPLEX, Complexity.EXPERT] else 0.9,
    )


def format_route_output(decision: RouteDecision) -> str:
    """Format routing decision for display."""
    level_icons = {
        "overdrive": "⚡🔥", "ultra": "🔥", "mega_brain": "🧠", "brain": "⚡", "normal": "💬"
    }
    icon = level_icons.get(decision.level, "💬")
    
    sat = decision.sentiment_analysis
    sat_icon = {"satisfeito": "😊", "neutro": "😐", "insatisfeito": "😞"}
    
    lines = [
        f"\n{icon}  MEGA BRAIN ROUTER",
        "─" * 50,
        f"  Input Level:  {decision.level.upper()}",
        f"  Model:        {decision.model}",
        f"  Squad:        {decision.squad or 'Nenhum'}",
        f"  Complexity:   {decision.complexity.value}",
        f"  Sentiment:    {decision.sentiment}",
        f"  Keywords:     {decision.keywords_found or 'Nenhuma'}",
        f"  Confidence:   {decision.confidence:.0%}",
        f"  Reasoning:    {decision.reasoning}",
        "─" * 20,
        f"  Análise de Sentimento (via {sat.source.upper()}):",
        f"    Satisfação: {sat_icon.get(sat.satisfaction, '😐')} {sat.satisfaction}",
        f"    Tom:        {sat.tone}",
        f"    Emoção:     {sat.emotion}",
        f"    Motivo:     {sat.reasoning}",
        "─" * 50,
    ]
    return "\n".join(lines)
