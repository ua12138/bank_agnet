def metric_tool(incident: dict) -> dict:
    return {"metric": incident.get("metric"), "value": 980, "signal": "high"}
