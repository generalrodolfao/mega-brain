import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "fast": "google/gemini-2.5-flash-lite",
    "standard": "openai/gpt-4o",
    "premium": "anthropic/claude-sonnet-4",
    "reasoning": "openai/o3-mini",
    "squad_agent": "openai/gpt-4o-mini",
    "squad_chief": "anthropic/claude-sonnet-4",
}

ROUTE_KEYWORDS = {
    "squad": [
        "mega brain", "overdrive", "modo deus", "squad",
        "todos os agentes", "200%", "full power", "deep research",
    ],
    "premium": [
        "análise profunda", "estratégia completa", "complexo",
        "analise profunda", "estrategia completa",
    ],
    "standard": [
        "analise", "análise", "estratégia", "brain",
        "copy", "copywriting", "marketing",
    ],
}

SQUAD_AGENTS = {
    "copywriter": {
        "model": "openai/gpt-4o-mini",
        "system_prompt": "Você é um copywriter sênior. Escreva copy persuasiva e criativa.",
    },
    "strategist": {
        "model": "openai/gpt-4o",
        "system_prompt": "Você é um estrategista de marketing. Crie estratégias claras e acionáveis.",
    },
    "social_media": {
        "model": "openai/gpt-4o-mini",
        "system_prompt": "Você é um especialista em redes sociais. Adapte conteúdo para cada plataforma.",
    },
    "seo": {
        "model": "openai/gpt-4o-mini",
        "system_prompt": "Você é um especialista em SEO. Otimize conteúdo com palavras-chave e estrutura.",
    },
    "designer": {
        "model": "openai/gpt-4o-mini",
        "system_prompt": "Você é um diretor de arte. Descreva briefings visuais para designers.",
    },
    "reviewer": {
        "model": "anthropic/claude-sonnet-4",
        "system_prompt": "Você é um revisor de qualidade. Revise e sugira melhorias para o conteúdo.",
    },
}
