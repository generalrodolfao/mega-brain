from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from nodes.classify import analyze_sentiment, detect_complexity, decide_route
from nodes.respond import respond_fast, respond_standard, respond_premium
from nodes.squad import squad_fanout, squad_consolidate


def route_decision(state: AgentState) -> str:
    return state.get("route", "fast")


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Classification pipeline
    graph.add_node("analyze_sentiment", analyze_sentiment)
    graph.add_node("detect_complexity", detect_complexity)
    graph.add_node("decide_route", decide_route)

    # Response nodes (one per tier)
    graph.add_node("respond_fast", respond_fast)
    graph.add_node("respond_standard", respond_standard)
    graph.add_node("respond_premium", respond_premium)

    # Squad pipeline
    graph.add_node("squad_fanout", squad_fanout)
    graph.add_node("squad_consolidate", squad_consolidate)

    # Edges
    graph.add_edge(START, "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "detect_complexity")
    graph.add_edge("detect_complexity", "decide_route")

    graph.add_conditional_edges(
        "decide_route",
        route_decision,
        {
            "fast": "respond_fast",
            "standard": "respond_standard",
            "premium": "respond_premium",
            "squad": "squad_fanout",
        },
    )

    graph.add_edge("respond_fast", END)
    graph.add_edge("respond_standard", END)
    graph.add_edge("respond_premium", END)

    graph.add_edge("squad_fanout", "squad_consolidate")
    graph.add_edge("squad_consolidate", END)

    return graph.compile(checkpointer=MemorySaver())
