"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""诊断编排层。

支持两种执行方式：
- classic：顺序执行（去重 -> 审批 -> ReAct）
- langgraph：用状态图显式编排节点和路由
"""

from typing import Any, TypedDict

from hz_bank_aiops.agent import LangGraphReActExecutor, LangGraphReactUnavailableError, ReActAgent
from hz_bank_aiops.models import (
    ApprovalStatus,
    DiagnosisResult,
    IncidentPayload,
    RootCauseCandidate,
)
from hz_bank_aiops.service.control_center import IncidentControlCenter


class WorkflowUnavailableError(RuntimeError):
    """WorkflowUnavailableError：封装该领域职责，供上层流程统一调用。"""

    pass


class _IncidentState(TypedDict, total=False):
    """_IncidentState：封装该领域职责，供上层流程统一调用。"""
    incident: IncidentPayload
    dedup_result: dict[str, Any]
    approval_status: ApprovalStatus
    result: DiagnosisResult


class IncidentDiagnosisWorkflow:
    """IncidentDiagnosisWorkflow：封装该领域职责，供上层流程统一调用。"""

    def __init__(
        self,
        agent: ReActAgent,
        control_center: IncidentControlCenter,
        workflow_engine: str = "langgraph",
        enable_dedup: bool = True,
        enable_human_approval: bool = True,
        react_cot_enabled: bool = False,
        react_cot_max_chars: int = 240,
        react_cot_max_entries: int = 16,
        react_memory_enabled: bool = True,
        react_context_window_steps: int = 3,
        react_summary_max_chars: int = 480,
        react_summary_max_entries: int = 12,
    ) -> None:
        # 复用同一套 Agent 与控制中心，保证 classic/langgraph 逻辑一致
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.agent = agent
        self.control_center = control_center
        self.workflow_engine = workflow_engine
        self.enable_dedup = enable_dedup
        self.enable_human_approval = enable_human_approval
        self.react_cot_enabled = react_cot_enabled
        self.react_cot_max_chars = react_cot_max_chars
        self.react_cot_max_entries = react_cot_max_entries
        self.react_memory_enabled = react_memory_enabled
        self.react_context_window_steps = react_context_window_steps
        self.react_summary_max_chars = react_summary_max_chars
        self.react_summary_max_entries = react_summary_max_entries

        self._langgraph_react: LangGraphReActExecutor | None = None
        try:
            self._langgraph_react = LangGraphReActExecutor(
                agent=agent,
                cot_enabled=self.react_cot_enabled,
                cot_max_chars=self.react_cot_max_chars,
                cot_max_entries=self.react_cot_max_entries,
                memory_enabled=self.react_memory_enabled,
                context_window_steps=self.react_context_window_steps,
                summary_max_chars=self.react_summary_max_chars,
                summary_max_entries=self.react_summary_max_entries,
            )
        except LangGraphReactUnavailableError:
            self._langgraph_react = None

        self._graph = self._build_graph() if workflow_engine == "langgraph" else None

    def execute(self, incident: IncidentPayload) -> DiagnosisResult:
        """execute：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if self._graph is None:
            return self._execute_classic(incident)
        result = self._graph.invoke({"incident": incident})
        return result["result"]

    def _execute_classic(self, incident: IncidentPayload) -> DiagnosisResult:
        """_execute_classic：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if self.enable_dedup:
            dedup = self.control_center.check_duplicate(incident)
            if dedup.get("is_duplicate"):
                return self._duplicate_result(incident, dedup)

        approval = self.control_center.ensure_approval(
            incident=incident,
            enabled=self.enable_human_approval,
        )
        if approval.status == ApprovalStatus.pending:
            return self._pending_result(incident)
        if approval.status == ApprovalStatus.rejected:
            return self._rejected_result(incident, approval.comment)

        return self._react_diagnose(incident, workflow_engine="classic")

    def _build_graph(self):
        """_build_graph：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise WorkflowUnavailableError("langgraph package is required for langgraph workflow") from exc

        def dedup_node(state: _IncidentState) -> _IncidentState:
            # 去重节点：不启用时返回“非重复”占位结果
            """dedup_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            incident = state["incident"]
            if not self.enable_dedup:
                return {"dedup_result": {"is_duplicate": False}}
            return {"dedup_result": self.control_center.check_duplicate(incident)}

        def route_after_dedup(state: _IncidentState) -> str:
            # 重复告警直接短路结束，非重复进入审批
            """route_after_dedup：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            return "duplicate" if state.get("dedup_result", {}).get("is_duplicate") else "approval"

        def duplicate_node(state: _IncidentState) -> _IncidentState:
            """duplicate_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            incident = state["incident"]
            dedup = state.get("dedup_result", {})
            return {"result": self._duplicate_result(incident, dedup)}

        def approval_node(state: _IncidentState) -> _IncidentState:
            """approval_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            incident = state["incident"]
            row = self.control_center.ensure_approval(
                incident=incident,
                enabled=self.enable_human_approval,
            )
            return {"approval_status": row.status}

        def route_after_approval(state: _IncidentState) -> str:
            # 审批放行才进入 ReAct，否则进入 pending/rejected 分支
            """route_after_approval：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            status = state.get("approval_status", ApprovalStatus.pending)
            if status in {ApprovalStatus.approved, ApprovalStatus.auto_approved}:
                return "react"
            if status == ApprovalStatus.rejected:
                return "rejected"
            return "pending"

        def pending_node(state: _IncidentState) -> _IncidentState:
            """pending_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            return {"result": self._pending_result(state["incident"])}

        def rejected_node(state: _IncidentState) -> _IncidentState:
            """rejected_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            return {"result": self._rejected_result(state["incident"], "rejected by approver")}

        def react_node(state: _IncidentState) -> _IncidentState:
            """react_node：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
            result = self._react_diagnose(state["incident"], workflow_engine="langgraph")
            return {"result": result}

        graph = StateGraph(_IncidentState)
        graph.add_node("dedup", dedup_node)
        graph.add_node("duplicate", duplicate_node)
        graph.add_node("approval", approval_node)
        graph.add_node("pending", pending_node)
        graph.add_node("rejected", rejected_node)
        graph.add_node("react", react_node)

        graph.add_edge(START, "dedup")
        graph.add_conditional_edges("dedup", route_after_dedup, {"duplicate": "duplicate", "approval": "approval"})
        graph.add_conditional_edges(
            "approval",
            route_after_approval,
            {"react": "react", "pending": "pending", "rejected": "rejected"},
        )
        graph.add_edge("duplicate", END)
        graph.add_edge("pending", END)
        graph.add_edge("rejected", END)
        graph.add_edge("react", END)
        return graph.compile()

    def _react_diagnose(self, incident: IncidentPayload, workflow_engine: str) -> DiagnosisResult:
        """_react_diagnose：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        payload = incident.model_dump(mode="json")
        if workflow_engine == "langgraph" and self._langgraph_react is not None:
            result = self._langgraph_react.run(payload)
            result.result_json["react_engine"] = "langgraph"
            return result
        result = self.agent.run(payload)
        result.result_json["react_engine"] = "classic"
        return result

    def _duplicate_result(self, incident: IncidentPayload, dedup: dict[str, Any]) -> DiagnosisResult:
        """_duplicate_result：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return DiagnosisResult(
            incident_id=incident.incident_id,
            root_cause_top1="Duplicate incident suppressed",
            root_cause_candidates=[RootCauseCandidate(cause="Duplicate incident suppressed", confidence=1.0)],
            evidence=[f"duplicate_of={dedup.get('duplicate_of', '')}"],
            suggestions=["Merge with existing incident and continue observation."],
            confidence=1.0,
            result_json={
                "workflow_engine": self.workflow_engine,
                "deduplicated": True,
                "duplicate_of": dedup.get("duplicate_of", ""),
            },
        )

    def _pending_result(self, incident: IncidentPayload) -> DiagnosisResult:
        """_pending_result：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return DiagnosisResult(
            incident_id=incident.incident_id,
            root_cause_top1="Waiting for human approval",
            root_cause_candidates=[RootCauseCandidate(cause="Waiting for human approval", confidence=0.0)],
            evidence=["approval_status=pending"],
            suggestions=["Approve incident via /api/v1/approvals/{incident_id} then retry diagnosis."],
            confidence=0.0,
            result_json={"workflow_engine": self.workflow_engine, "approval_status": "pending"},
        )

    def _rejected_result(self, incident: IncidentPayload, comment: str) -> DiagnosisResult:
        """_rejected_result：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return DiagnosisResult(
            incident_id=incident.incident_id,
            root_cause_top1="Diagnosis rejected by approver",
            root_cause_candidates=[
                RootCauseCandidate(cause="Diagnosis rejected by approver", confidence=0.0)
            ],
            evidence=[comment or "approval_status=rejected"],
            suggestions=["Escalate to incident manager if diagnosis is still required."],
            confidence=0.0,
            result_json={"workflow_engine": self.workflow_engine, "approval_status": "rejected"},
        )
