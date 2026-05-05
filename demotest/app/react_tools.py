"""??????????????????????????"""

from __future__ import annotations

"""demotest 的降格 ReAct 工具与执行器。"""

from dataclasses import dataclass
from typing import Any

import httpx


def tool_metric_probe(incident: dict[str, Any]) -> dict[str, Any]:
    """伪指标探针：返回固定结构的高负载信号。"""
    return {
        "host_count": len(incident.get("hosts", [])),
        "signals": ["mysql.connections high", "api timeout up", "5xx up"],
    }


def tool_change_probe(incident: dict[str, Any]) -> dict[str, Any]:
    """伪变更探针：回放 recent_change_ids。"""
    return {
        "changes": incident.get("recent_change_ids", []),
        "comment": "recent release exists before incident window",
    }


def _http_error_text(resp: httpx.Response) -> str:
    """尽量提取可读错误信息，便于调试 MCP 报错。"""
    try:
        body = resp.json()
        if isinstance(body, dict):
            detail = body.get("detail")
            if detail:
                return str(detail)
        return str(body)
    except Exception:  # noqa: BLE001
        text = resp.text.strip()
        return text[:500] if text else f"HTTP {resp.status_code}"


def tool_rag_probe(
    base_url: str,
    query: str,
    timeout_sec: float = 60.0,
    top_k: int = 1,
    candidate_multiplier: int = 1,
    fast_mode: bool = True,
    use_memory: bool = False,
) -> dict[str, Any]:
    """调用 RAG MCP。

    策略：
    - 先 health 检查，快速发现服务不可用/未配置问题
    - 若 key 未配置，降级调用 lightweight 工具以保证 demo 通路可观测
    """
    base = base_url.rstrip("/")
    timeout = httpx.Timeout(timeout=timeout_sec, connect=min(timeout_sec, 10.0))
    try:
        with httpx.Client(timeout=timeout) as client:
            health = client.get(f"{base}/health")
            if health.status_code >= 400:
                return {"ok": False, "error": f"health check failed: {_http_error_text(health)}"}

            health_body = health.json()
            key_ready = bool(health_body.get("siliconflow_key_configured", False))
            if not key_ready:
                # Without key, rag.query may fail after retrieval path enters embedding/chat calls.
                # Keep demotest pass-through by calling a lightweight MCP tool.
                fallback_payload = {
                    "name": "rag.list_documents",
                    "arguments": {"kb_id": "hz-bank-demo", "limit": 2},
                }
                fallback = client.post(f"{base}/tools/call", json=fallback_payload)
                if fallback.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"siliconflow key missing and fallback failed: {_http_error_text(fallback)}",
                    }
                return {
                    "ok": True,
                    "mode": "rag.list_documents",
                    "note": "siliconflow key missing; rag.query skipped in demotest",
                    "result": fallback.json(),
                }

            payload = {
                "name": "rag.query",
                "arguments": {
                    "kb_id": "hz-bank-demo",
                    "query": query,
                    "top_k": top_k,
                    "candidate_multiplier": candidate_multiplier,
                    "fast_mode": fast_mode,
                    "use_memory": use_memory,
                },
            }
            resp = client.post(f"{base}/tools/call", json=payload)
            if resp.status_code >= 400:
                return {"ok": False, "error": _http_error_text(resp), "status_code": resp.status_code}
            return {"ok": True, "mode": "rag.query", "result": resp.json()}
    except httpx.TimeoutException:
        return {
            "ok": False,
            "error": f"timed out (>{timeout_sec}s), try increasing HZ_AIOPS_DEMO_RAG_TIMEOUT_SEC",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@dataclass
class PseudoReActEngine:
    """PseudoReActEngine???????????????????"""
    rag_mcp_base_url: str
    rag_timeout_sec: float = 60.0
    rag_query_top_k: int = 1
    rag_candidate_multiplier: int = 1
    rag_fast_mode: bool = True
    rag_use_memory: bool = False

    def run(self, incident: dict[str, Any]) -> dict[str, Any]:
        """按固定三步执行 pseudo ReAct，并输出完整 reasoning。"""
        reasoning: list[dict[str, Any]] = []

        thought_1 = "Step1: check realtime metrics to verify actual impact."
        obs_1 = tool_metric_probe(incident)
        reasoning.append({"thought": thought_1, "action": "metric_probe", "observation": obs_1})

        thought_2 = "Step2: check whether change activity can explain symptom burst."
        obs_2 = tool_change_probe(incident)
        reasoning.append({"thought": thought_2, "action": "change_probe", "observation": obs_2})

        thought_3 = "Step3: query RAG MCP for similar historical incidents."
        query = f"{incident.get('system', '')} {incident.get('service', '')} incident root cause"
        obs_3 = tool_rag_probe(
            self.rag_mcp_base_url,
            query=query,
            timeout_sec=self.rag_timeout_sec,
            top_k=self.rag_query_top_k,
            candidate_multiplier=self.rag_candidate_multiplier,
            fast_mode=self.rag_fast_mode,
            use_memory=self.rag_use_memory,
        )
        reasoning.append({"thought": thought_3, "action": "rag_probe", "observation": obs_3})

        summary = (
            "Pseudo-ReAct conclusion: DB pressure + release change are primary drivers, "
            "RAG evidence consulted for historical similarity."
        )
        return {"summary": summary, "reasoning": reasoning}
