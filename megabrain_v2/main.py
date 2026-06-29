import asyncio
from langchain_core.messages import HumanMessage
from graph import build_graph


async def run():
    app = build_graph()
    config = {"configurable": {"thread_id": "demo-session"}}

    messages = [
        "Qual a data e hora agora?",
        "Analise o mercado de IA no Brasil e crie uma estratégia de entrada",
        "mega brain: crie uma campanha completa de marketing para o Café com Dados",
    ]

    for i, text in enumerate(messages):
        print(f"\n{'='*60}")
        print(f"INPUT [{i+1}]: {text[:80]}...")
        print(f"{'='*60}")

        async for event in app.astream(
            {"messages": [HumanMessage(content=text)]},
            config,
            stream_mode="updates",
        ):
            for node_name, update in event.items():
                print(f"  [{node_name}] ✓")

        state = await app.aget_state(config)
        response = state.values.get("response", "")
        route = state.values.get("route", "")
        model = state.values.get("model_used", "")

        print(f"\n  Route: {route}")
        print(f"  Model: {model}")
        print(f"\nRESPONSE:\n{response[:500]}{'...' if len(response) > 500 else ''}")
        print(f"\n{'-'*60}")

    print("\nDone! All 3 examples processed.")


if __name__ == "__main__":
    asyncio.run(run())
