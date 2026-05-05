from tools.search_manual import search_manual


def handle_call(payload: dict) -> dict:
    tool_name = payload["name"]
    arguments = payload["arguments"]
    registry = {"search_manual": search_manual}
    if tool_name not in registry:
        return {"ok": False, "error": f"tool not found: {tool_name}"}
    return {"ok": True, "data": registry[tool_name](**arguments)}
