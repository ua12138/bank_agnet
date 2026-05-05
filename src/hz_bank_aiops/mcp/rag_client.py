from __future__ import annotations

"""RAG MCP HTTP 客户端。

约定通信格式：
- 健康检查：GET /health
- 工具调用：POST /tools/call，body 为 {"name": "...", "arguments": {...}}
"""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class RagCallResult:
    """MCP 调用结果包装。"""

    ok: bool
    data: dict[str, Any]
    error: str = ""


class RagMCPClient:
    """
    Client for sibling `hz_bank_rag` MCP wrapper service.
    Unified protocol: `/tools/call` with `name` + `arguments`.
    """

    def __init__(self, base_url: str, timeout_sec: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def health(self) -> RagCallResult:
        """探测 MCP 服务健康状态。"""
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                resp = client.get(f"{self.base_url}/health")
                resp.raise_for_status()
                return RagCallResult(ok=True, data=resp.json())
        except Exception as exc:  # noqa: BLE001
            return RagCallResult(ok=False, data={}, error=str(exc))

    def query(self, kb_id: str, query: str, top_k: int = 5) -> RagCallResult:
        """调用 RAG 检索工具。"""

        payload = {
            "name": "rag.query",
            "arguments": {"kb_id": kb_id, "query": query, "top_k": top_k},
        }
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                resp = client.post(f"{self.base_url}/tools/call", json=payload)
                resp.raise_for_status()
                return RagCallResult(ok=True, data=resp.json())
        except Exception as exc:  # noqa: BLE001
            return RagCallResult(ok=False, data={}, error=str(exc))
