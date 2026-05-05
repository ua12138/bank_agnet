"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""运维诊断工具集。

当前实现以 Mock 数据为主，用于打通端到端链路；
后续可在同名类中替换成真实 API 调用。
"""

from typing import Any

from hz_bank_aiops.mcp import RagMCPClient
from hz_bank_aiops.tools.base import Tool


class ZabbixMetricsTool(Tool):
    """ZabbixMetricsTool：封装该领域职责，供上层流程统一调用。"""

    name = "zabbix_realtime_metrics"
    description = "Query realtime metrics from zabbix"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        # 输入统一约定：payload["incident"] 为 Incident 字典
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        incident = payload.get("incident", {})
        hosts = incident.get("hosts", [])
        # 返回结构要稳定，便于 LLM 在 observation 中做模式识别
        return {
            "source": "mock-zabbix",
            "hosts": hosts,
            "metrics_snapshot": [
                {"host": host, "cpu_usage": 78.2, "mem_usage": 72.5, "tcp_retrans_rate": 1.8}
                for host in hosts
            ],
        }


class DorisHistoryTool(Tool):
    """DorisHistoryTool：封装该领域职责，供上层流程统一调用。"""

    name = "doris_history_lookup"
    description = "Lookup historical incidents and diagnosis results in doris"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        incident = payload.get("incident", {})
        service = incident.get("service", "")
        return {
            "source": "mock-doris",
            "service": service,
            "historical_incidents": [
                {
                    "incident_id": "inc_hist_1001",
                    "root_cause": "DB slow SQL leads to connection pool saturation",
                    "confidence": 0.82,
                }
            ],
        }


class XueLangChangeTool(Tool):
    """XueLangChangeTool：封装该领域职责，供上层流程统一调用。"""

    name = "xuelang_change_lookup"
    description = "Lookup recent deployment changes from xuelang"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        incident = payload.get("incident", {})
        changes = incident.get("recent_change_ids", [])
        return {
            "source": "mock-xuelang",
            "recent_changes": [
                {"change_id": change_id, "owner": "release-bot", "summary": "payment-api release"}
                for change_id in changes
            ],
        }


class RagCaseTool(Tool):
    """RagCaseTool：封装该领域职责，供上层流程统一调用。"""

    name = "rag_case_search"
    description = "Query MCP RAG service for similar cases"

    def __init__(self, rag_client: RagMCPClient, kb_id: str = "hz-bank-demo") -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.rag_client = rag_client
        self.kb_id = kb_id

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        incident = payload.get("incident", {})
        system = incident.get("system", "")
        service = incident.get("service", "")
        summary = f"{system} {service} {incident.get('severity', '')} incident diagnosis"

        # 统一走 MCP `/tools/call`，避免多协议并存导致对接复杂度上升
        query_res = self.rag_client.query(kb_id=self.kb_id, query=summary, top_k=3)
        if not query_res.ok:
            return {"source": "rag-mcp", "ok": False, "error": query_res.error}
        return {"source": "rag-mcp", "ok": True, "result": query_res.data}


def build_default_tools(rag_client: RagMCPClient) -> list[Tool]:
    """build_default_tools：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""

    return [
        ZabbixMetricsTool(),
        DorisHistoryTool(),
        XueLangChangeTool(),
        RagCaseTool(rag_client=rag_client),
    ]
