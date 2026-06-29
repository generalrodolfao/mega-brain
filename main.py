"""
Mega Brain — Main Entry Point.

CLI interface for the Mega Brain system. Supports:
  - Voice input (microphone or file)
  - Text input (direct or file)
  - Sentiment routing
  - Squad activation
  - Dashboard server
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

from core.router import route, format_route_output
from core.engine import Orchestrator, StateManager


def print_banner():
    """Print the Mega Brain ASCII banner."""
    banner = """
    ╔══════════════════════════════════════════╗
    ║           🧠  MEGA BRAIN  v1.0          ║
    ║  Sistema de Orquestração Multi-Agente     ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)


def setup_pipeline(orchestrator):
    """Register the standard Mega Brain pipeline steps."""

    async def voice_step(text, step):
        return {"transcribed": text, "format": "text"}

    async def sentiment_step(text, step):
        decision = route(text)
        return {
            "level": decision.level,
            "model": decision.model,
            "squad": decision.squad,
            "complexity": decision.complexity.value,
            "sentiment": decision.sentiment,
            "reasoning": decision.reasoning,
        }

    async def squad_step(text, step):
        route_decision = route(text)
        if route_decision.squad:
            return {
                "activated": True,
                "squad": route_decision.squad,
                "agents": 7,
                "status": "delegating",
            }
        return {"activated": False, "squad": None}

    async def output_step(text, step):
        return {
            "response": f"Processado via rota: {route(text).level}",
            "format": "text",
        }

    orchestrator.register_pipeline([
        {"name": "voice_input", "handler": voice_step},
        {"name": "sentiment_router", "handler": sentiment_step},
        {"name": "model_router", "handler": sentiment_step},
        {"name": "squad_activation", "handler": squad_step},
        {"name": "execution", "handler": squad_step},
        {"name": "consolidation", "handler": output_step},
        {"name": "dashboard", "handler": output_step},
    ])

    return orchestrator


async def interactive_mode():
    """Run Mega Brain in interactive text mode."""
    print_banner()
    print("  Digite 'sair' para encerrar")
    print("  Digite 'server' para iniciar o painel")
    print("  Digite 'demo' para uma demonstração automática")
    print()

    orchestrator = setup_pipeline(Orchestrator())

    while True:
        try:
            text = input("🧠  Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in ("sair", "exit", "quit"):
            print("  Mega Brain desativado. Até mais! 🧠")
            break
        elif user_input.lower() == "server":
            print("  Iniciando painel em http://localhost:3001")
            from core.server import run_server
            run_server()
            break
        if text.lower() == "demo":
            print("  Iniciando demonstração automática...\n")
            await run_demo()
            continue

        print(format_route_output(route(text)))

        if route(text).squad:
            print(f"  🎯 Ativando squad: {route(text).squad}")
            print(f"  🤖 7 agentes mobilizados")
            print(f"  ⚡ Processando...")

        print()


async def run_demo():
    """Run a demonstration of the routing system."""
    test_cases = [
        "Qual a previsão do tempo hoje?",
        "Brain, cria um post para o LinkedIn",
        "Mega Brain, quero uma estratégia de lançamento completa com copy chief",
    ]

    for text in test_cases:
        print(f"  Input: '{text}'")
        print(format_route_output(route(text)))
        if route(text).squad:
            print(f"  🎯 ATIVANDO SQUAD: {route(text).squad}")
        print()
        await asyncio.sleep(1)

    print("  🧠 Demonstração concluída!")
    print()
    print("  Para testar o painel com animação:")
    print("    python main.py server")


def main():
    parser = argparse.ArgumentParser(description="Mega Brain — Multi-Agent AI Orchestration")
    parser.add_argument("mode", nargs="?", default="interactive",
                        choices=["interactive", "server", "demo", "route"],
                        help="Modo de execução")
    parser.add_argument("--text", "-t", help="Texto para roteamento (modo route)")
    parser.add_argument("--port", "-p", type=int, default=3001, help="Porta do dashboard")
    parser.add_argument("--host", default="localhost", help="Host do dashboard")

    args = parser.parse_args()

    if args.mode == "server":
        print_banner()
        print(f"  Iniciando painel em http://{args.host}:{args.port}")
        print("  Pressione Ctrl+C para parar\n")
        from core.server import run_server
        run_server(host=args.host, port=args.port)

    elif args.mode == "demo":
        print_banner()
        print("  Demonstração do Roteador Mega Brain\n")
        asyncio.run(run_demo())

    elif args.mode == "route":
        if not args.text:
            print("Use --text ou -t para fornecer o texto.")
            print("Ex: python main.py route -t 'Mega Brain, cria uma estratégia'")
            return
        print_banner()
        print(format_route_output(route(args.text)))
        if route(args.text).squad:
            print(f"  🎯 Squad ativado: {route(args.text).squad}")

    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
