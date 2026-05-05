def plan_node(state: dict) -> tuple[dict, str]:
    state["history"].append("plan")
    return state, "tool"
