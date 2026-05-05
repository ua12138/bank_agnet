"""????????????????Agent????????"""

from __future__ import annotations

"""运行时装配层。

该模块将配置、存储、工具、Agent、工作流、通知器组装为可执行运行时。
"""

from datetime import UTC, datetime
from typing import Any

from hz_bank_aiops.agent import ReActAgent
from hz_bank_aiops.config import Settings
from hz_bank_aiops.mcp import RagMCPClient
from hz_bank_aiops.models import (
    ApprovalRecord,
    ApprovalStatus,
    DiagnosisResult,
    IncidentPayload,
    NotifyStatus,
)
from hz_bank_aiops.notifier import FeishuNotifier
from hz_bank_aiops.service.control_center import IncidentControlCenter
from hz_bank_aiops.service.workflow import IncidentDiagnosisWorkflow, WorkflowUnavailableError
from hz_bank_aiops.storage import TaskStore, build_task_store
from hz_bank_aiops.tools import build_default_tools


class DiagnosisRuntime:
    """诊断系统运行时入口。"""

    def __init__(self, settings: Settings) -> None:
        """????????????????????"""
        self.settings = settings
        # 1) 存储层
        self.store: TaskStore = build_task_store(settings)
        # 2) 外部服务客户端
        self.rag_client = RagMCPClient(
            base_url=settings.rag_mcp_base_url,
            timeout_sec=settings.mcp_request_timeout_sec,
        )
        # 3) Tool 与 Agent
        self.tools = build_default_tools(rag_client=self.rag_client)
        self.agent = ReActAgent(tools=self.tools, max_steps=6)
        # 4) 治理中台（去重/审批）
        self.control_center = IncidentControlCenter(
            store=self.store,
            dedup_window_sec=settings.dedup_window_sec,
        )
        resolved_engine = settings.workflow_engine
        try:
            # 5) 编排层（优先按配置引擎）
            self.workflow = IncidentDiagnosisWorkflow(
                agent=self.agent,
                control_center=self.control_center,
                workflow_engine=settings.workflow_engine,
                enable_dedup=settings.enable_dedup,
                enable_human_approval=settings.enable_human_approval,
                react_cot_enabled=settings.react_cot_enabled,
                react_cot_max_chars=settings.react_cot_max_chars,
                react_cot_max_entries=settings.react_cot_max_entries,
                react_memory_enabled=settings.react_memory_enabled,
                react_context_window_steps=settings.react_context_window_steps,
                react_summary_max_chars=settings.react_summary_max_chars,
                react_summary_max_entries=settings.react_summary_max_entries,
            )
        except WorkflowUnavailableError:
            # 如果 langgraph 不可用且允许降级，则回退到 classic
            if not settings.langgraph_fallback_to_classic:
                raise
            resolved_engine = "classic"
            self.workflow = IncidentDiagnosisWorkflow(
                agent=self.agent,
                control_center=self.control_center,
                workflow_engine="classic",
                enable_dedup=settings.enable_dedup,
                enable_human_approval=settings.enable_human_approval,
                react_cot_enabled=settings.react_cot_enabled,
                react_cot_max_chars=settings.react_cot_max_chars,
                react_cot_max_entries=settings.react_cot_max_entries,
                react_memory_enabled=settings.react_memory_enabled,
                react_context_window_steps=settings.react_context_window_steps,
                react_summary_max_chars=settings.react_summary_max_chars,
                react_summary_max_entries=settings.react_summary_max_entries,
            )
        self.resolved_workflow_engine = resolved_engine
        # 6) 通知层
        self.notifier = FeishuNotifier(
            webhook_url=settings.feishu_webhook_url,
            timeout_sec=settings.webhook_timeout_sec,
        )

    def init_schema(self) -> None:
        """初始化数据库表结构。"""
        self.store.init_schema()

    def health(self) -> dict[str, Any]:
        """聚合系统健康状态，供 API `/health` 直接返回。"""
        rag_health = self.rag_client.health()
        return {
            "app": self.settings.app_name,
            "env": self.settings.env,
            "task_db_kind": self.settings.task_db_kind,
            "workflow_engine": self.settings.workflow_engine,
            "resolved_workflow_engine": self.resolved_workflow_engine,
            "react_cot_enabled": self.settings.react_cot_enabled,
            "react_cot_max_chars": self.settings.react_cot_max_chars,
            "react_cot_max_entries": self.settings.react_cot_max_entries,
            "react_memory_enabled": self.settings.react_memory_enabled,
            "react_context_window_steps": self.settings.react_context_window_steps,
            "react_summary_max_chars": self.settings.react_summary_max_chars,
            "react_summary_max_entries": self.settings.react_summary_max_entries,
            "rag_mcp_ok": rag_health.ok,
            "rag_mcp_data": rag_health.data,
            "rag_mcp_error": rag_health.error,
        }

    def submit_incident(self, incident: IncidentPayload, priority: str = "P2") -> int:
        """提交 incident 到任务队列。"""
        return self.store.enqueue_incident(incident.model_dump(mode="json"), priority=priority)

    def get_task(self, task_id: int):
        """查询任务。"""
        return self.store.get_task(task_id)

    def list_tasks(self, limit: int = 50):
        """查询最近任务列表。"""
        return self.store.list_tasks(limit=limit)

    def get_approval(self, incident_id: str) -> ApprovalRecord | None:
        """读取审批状态。"""
        return self.store.get_approval(incident_id)

    def submit_approval(
        self,
        incident_id: str,
        status: ApprovalStatus,
        approver: str,
        comment: str = "",
    ) -> ApprovalRecord:
        """提交人工审批结论。"""
        return self.control_center.submit_approval(
            incident_id=incident_id,
            status=status,
            approver=approver,
            comment=comment,
        )

    def process_one_task(self, worker_id: str) -> dict[str, Any]:
        """消费并处理一条任务。

        主流程：
        1. 抢占任务
        2. 执行编排诊断
        3. 落库结果
        4. 发送通知（可选）
        5. 更新任务状态
        """
        claim = self.store.claim_next_task(worker_id)
        if not claim.claimed or not claim.task:
            return {"claimed": False, "message": "no pending task"}

        task = claim.task
        try:
            incident = IncidentPayload.model_validate(task.payload_json)
            result = self.workflow.execute(incident)
            result.created_at = datetime.now(UTC)
            self.store.save_result(result)

            notify_status = self._notify_if_needed(task.need_notify, result)
            self.store.mark_done(task_id=task.id or 0, notify_status=notify_status)

            return {
                "claimed": True,
                "task_id": task.id,
                "incident_id": task.incident_id,
                "status": "DONE",
                "notify_status": notify_status.value,
                "result": result.model_dump(mode="json"),
            }
        except Exception as exc:  # noqa: BLE001
            # 失败不吞掉：记录错误并按重试策略回退任务状态
            self.store.mark_failed(
                task_id=task.id or 0,
                error_message=str(exc),
                retryable=True,
            )
            return {
                "claimed": True,
                "task_id": task.id,
                "incident_id": task.incident_id,
                "status": "FAILED",
                "error": str(exc),
            }

    def _notify_if_needed(self, need_notify: bool, result: DiagnosisResult) -> NotifyStatus:
        """按任务配置决定是否发送通知。"""
        if not need_notify:
            return NotifyStatus.skipped
        if not self.notifier.enabled():
            return NotifyStatus.failed
        res = self.notifier.send(result)
        return NotifyStatus.sent if res.ok else NotifyStatus.failed
