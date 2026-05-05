"""模块说明：该文件用于承载项目中的相关实现。"""

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
    """RagCallResult：封装该领域职责，供上层流程统一调用。"""

    ok: bool
    data: dict[str, Any]
    error: str = ""


class RagMCPClient:
    """RagMCPClient：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, base_url: str, timeout_sec: float = 8.0) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def health(self) -> RagCallResult:
        """health：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                resp = client.get(f"{self.base_url}/health")
                resp.raise_for_status()
                return RagCallResult(ok=True, data=resp.json())
        except Exception as exc:  # noqa: BLE001
            return RagCallResult(ok=False, data={}, error=str(exc))

    def query(self, kb_id: str, query: str, top_k: int = 5) -> RagCallResult:
        """query：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""

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
