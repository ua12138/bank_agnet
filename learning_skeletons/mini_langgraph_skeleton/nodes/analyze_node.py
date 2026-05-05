def analyze_node(state: dict) -> tuple[dict, str]:
    state["history"].append("analyze")
    if state.get("duplicate"):
        state["result"] = "duplicate incident"
    else:
        state["result"] = "continue diagnosis"
    return state, "final"
