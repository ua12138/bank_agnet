from nodes.analyze_node import analyze_node
from nodes.final_node import final_node
from nodes.plan_node import plan_node
from nodes.tool_node import tool_node


def run_graph(state: dict) -> dict:
    current = "plan"
    while current != "end":
        if current == "plan":
            state, current = plan_node(state)
        elif current == "tool":
            state, current = tool_node(state)
        elif current == "analyze":
            state, current = analyze_node(state)
        elif current == "final":
            state, current = final_node(state)
    return state
