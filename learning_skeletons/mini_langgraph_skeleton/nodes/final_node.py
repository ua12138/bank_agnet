def final_node(state: dict) -> tuple[dict, str]:
    state["history"].append("final")
    return state, "end"
