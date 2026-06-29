"""
OpenRouter Client — Unified API for accessing multiple LLMs.

Allows the Mega Brain router to actually call the selected model
(Gemini Flash, GPT-4o, Claude Opus, o3) through a single API.
"""

import os
import json
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("mega-brain")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Model ID mapping: our aliases → OpenRouter model IDs (verified working)
MODEL_MAP = {
    "gemini-2.0-flash-lite": "google/gemini-2.5-flash-lite",
    "gemini-2.5-flash-lite": "google/gemini-2.5-flash-lite",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4o": "openai/gpt-4o",
    "claude-sonnet-4": "anthropic/claude-sonnet-4",
    "o3": "openai/o3-mini",
    "o3-mini": "openai/o3-mini",
    "deepseek-chat": "deepseek/deepseek-chat",
    "default": "openai/gpt-4o-mini",
}


def resolve_model(alias: str) -> str:
    """Resolve internal model alias to OpenRouter model ID."""
    return MODEL_MAP.get(alias, MODEL_MAP["default"])


class OpenRouterClient:
    """
    Client for OpenRouter API.
    Handles auth, request formatting, and response parsing.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or DEFAULT_KEY
        self.client = httpx.Client(
            base_url=OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/mega-brain",
                "X-Title": "Mega Brain",
            },
            timeout=60,
        )

    def chat(
        self,
        model_alias: str,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        tools: Optional[list] = None,
    ) -> dict:
        """
        Send a chat completion request to OpenRouter.

        Args:
            model_alias: Internal model alias (e.g. "gpt-4o", "claude-sonnet-4")
            messages: List of {"role": "user"/"assistant", "content": str}
            system_prompt: Optional system message prepended to messages
            temperature: 0-2, higher = more creative
            max_tokens: Max tokens in response
            tools: Optional list of tool declarations (OpenAI format)

        Returns:
            Parsed response dict with "content", "model", "usage", "cost"
        """
        model_id = resolve_model(model_alias)
        
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        logger.info(f"  Chamando {model_id} ({model_alias})...")

        try:
            body = {
                "model": model_id,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens if max_tokens else None,
            }
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"

            response = self.client.post("/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            msg = choice["message"]
            usage = data.get("usage", {})

            result = {
                "model": data.get("model", model_id),
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                "finish_reason": choice.get("finish_reason", "stop"),
            }

            # Handle tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                from core.tools import process_tool_calls, TOOLS
                result["content"] = msg.get("content") or ""
                result["tool_calls"] = msg["tool_calls"]
                tool_responses = process_tool_calls(data["choices"])
                # Recursively call with tool responses
                all_msgs = full_messages + [msg] + tool_responses
                try:
                    follow_up = self.client.post("/chat/completions", json={
                        "model": model_id,
                        "messages": all_msgs,
                        "tools": tools or TOOLS,
                        "tool_choice": "auto",
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    })
                    follow_up.raise_for_status()
                    fdata = follow_up.json()
                    fchoice = fdata["choices"][0]
                    fusage = fdata.get("usage", {})
                    result["content"] = fchoice["message"]["content"] or ""
                    result["usage"]["prompt_tokens"] += fusage.get("prompt_tokens", 0)
                    result["usage"]["completion_tokens"] += fusage.get("completion_tokens", 0)
                    result["usage"]["total_tokens"] += fusage.get("total_tokens", 0)
                except Exception as e2:
                    logger.error(f"  Erro na chamada de follow-up: {e2}")
                    result["content"] = result.get("content", "") or "Processado."
            else:
                result["content"] = msg.get("content") or ""

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"  Erro na API OpenRouter: {e.response.status_code} - {e.response.text}")
            return {
                "content": f"Erro na API: {e.response.status_code}",
                "error": True,
                "model": model_id,
            }
        except Exception as e:
            logger.error(f"  Erro OpenRouter: {e}")
            return {
                "content": f"Erro: {str(e)}",
                "error": True,
                "model": model_id,
            }

    def route_and_chat(
        self,
        user_text: str,
        route_decision: dict,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Combine routing decision with actual model call.

        Args:
            user_text: The user's input text
            route_decision: Output from core.router.route()
            system_prompt: Optional system prompt override

        Returns:
            dict with content, model, level, squad, reasoning, usage
        """
        model_alias = route_decision.get("model", "default")
        squad_name = route_decision.get("squad")

        memory_context = ""
        try:
            from core.memory import load, format_for_prompt
            mem = format_for_prompt()
            if mem.strip():
                memory_context = f"\n\nMEMÓRIA DO USUÁRIO:\n{mem}\n"
        except Exception:
            pass

        jarvis_persona = (
            "Você é o J.A.R.V.I.S. — o cérebro operacional do Mega Brain.\n"
            "Personalidade: calmo, preciso, confiante, direto.\n"
            "Fale em português como um assistente elegante e eficiente.\n"
        )

        memory_instruction = (
            "VOCÊ TEM FERRAMENTAS:\n"
            "- save_memory: salve info do usuário (silencioso, não anuncie)\n"
            "- get_memory: consulte memórias\n"
            "- get_time: data/hora\n"
            "- calculate: cálculos\n"
            "Use quando necessário. Para conversas simples, responda naturalmente.\n"
        )

        conv_context = ""
        try:
            from core.memory import get_conversation
            hist = get_conversation(6)
            if hist:
                conv_context = "\n".join(hist) + "\n"
        except Exception:
            pass

        default_system = (
            f"{jarvis_persona}\n"
            f"{memory_instruction}\n"
            f"{memory_context}\n"
            f"{conv_context}\n"
            "Responda de forma natural e conversada, como se estivesse falando com alguém.\n"
            "Use formatação simples quando ajudar (**, ##, •, ```).\n"
            "Nada de listas enormes ou estrutura rígida — seja fluido.\n"
        )

        squad_system = (
            f"{jarvis_persona}\n"
            f"{memory_instruction}\n"
            f"{memory_context}\n"
            f"{conv_context}\n"
            "Você é o Copy Chief, líder de um squad de copywriting.\n"
            "Equipe: Strategist, Copywriter, Social Media, Designer, SEO, Reviewer.\n"
            "Produza um plano estratégico em seções claras.\n"
            "Seja direto, use formatação limpa.\n"
        )

        if route_decision["level"] in ("premium", "ultra", "mega_brain"):
            effective_system = system_prompt or squad_system
        else:
            effective_system = system_prompt or default_system

        from core.tools import TOOLS
        result = self.chat(
            model_alias=model_alias,
            messages=[{"role": "user", "content": user_text}],
            system_prompt=effective_system,
            temperature=0.8 if squad_name else 0.5,
            max_tokens=2048 if squad_name else 1024,
            tools=TOOLS,
        )

        result["level"] = route_decision["level"]
        result["squad"] = squad_name
        result["route_confidence"] = route_decision["confidence"]
        result["reasoning"] = route_decision["reasoning"]

        return result


# === Quick test ===
if __name__ == "__main__":
    from core.router import route

    client = OpenRouterClient()
    
    tests = [
        "Qual a capital do Brasil?",
        "Brain, me explica o que é machine learning",
        "Mega Brain, crie um plano de marketing para um SaaS de IA",
    ]

    for text in tests:
        print(f"\n{'='*60}")
        print(f"  Input: {text}")
        decision = route(text)
        print(f"  Route: {decision.level} → {decision.model} | squad={decision.squad}")

        result = client.route_and_chat(text, {
            "model": decision.model,
            "level": decision.level,
            "squad": decision.squad,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
        })

        content = result.get("content", "")
        print(f"  Response: {content[:200]}...")
        print(f"  Model: {result.get('model', '?')}")
        print(f"  Tokens: {result.get('usage', {}).get('total_tokens', '?')}")
