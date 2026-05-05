def tool_node(state: dict) -> tuple[dict, str]:
    state["history"].append("tool")
    state["observation"] = {"metric": "high"}
    return state, "analyze"
