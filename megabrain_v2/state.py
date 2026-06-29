from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def reducer_merge(left: list, right: list) -> list:
    result = list(left)
    for item in right:
        if item not in result:
            result.append(item)
    return result


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    route: str
    sentiment: str
    complexity: str

    squad_results: Annotated[list, reducer_merge]

    response: str
    model_used: str
    tokens_used: int
