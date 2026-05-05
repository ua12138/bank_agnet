from __future__ import annotations

"""经典 ReAct Agent 实现（无外部 LLM 依赖的可运行版本）。"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from hz_bank_aiops.models import DiagnosisResult, RootCauseCandidate, ToolTraceStep
from hz_bank_aiops.tools import Tool


class FunctionCall(BaseModel):
    """模拟 function calling 的调用对象。"""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMAction(BaseModel):
    """规划器输出动作。

    - kind=tool: 继续调用工具
    - kind=final: 输出最终结论
    """

    kind: str  # "tool" | "final"
    thought: str
    function_call: FunctionCall | None = None
    final_payload: dict[str, Any] = Field(default_factory=dict)


@dataclass
class PlannerContext:
    """规划器可见上下文。"""

    incident: dict[str, Any]
    steps: list[ToolTraceStep]
    completed_actions: set[str] | None = None
    memory_summary: str = ""


class MockOpsPlanner:
    """
    Deterministic planner that simulates a ReAct-capable LLM.
    """

    sequence = [
        "zabbix_realtime_metrics",
        "doris_history_lookup",
        "xuelang_change_lookup",
        "rag_case_search",
    ]

    def next_action(self, ctx: PlannerContext) -> LLMAction:
        """按固定顺序执行工具，模拟 LLM 的 ReAct 决策。"""
        done = ctx.completed_actions or {step.action for step in ctx.steps}
        for tool_name in self.sequence:
            if tool_name not in done:
                return LLMAction(
                    kind="tool",
                    thought=f"Need more evidence from {tool_name}.",
                    function_call=FunctionCall(
                        name=tool_name,
                        arguments={"incident": ctx.incident},
                    ),
                )
        return LLMAction(
            kind="final",
            thought="Enough evidence collected, generating final diagnosis.",
            final_payload=self._build_final(ctx.incident, ctx.steps),
        )

    def _build_final(self, incident: dict[str, Any], steps: list[ToolTraceStep]) -> dict[str, Any]:
        """根据已收集 observation 组装最终结果。"""
        evidence: list[str] = []
        for step in steps:
            observation = step.observation
            if step.action == "zabbix_realtime_metrics":
                evidence.append("Realtime host metrics show elevated retrans/usage.")
            if step.action == "doris_history_lookup":
                evidence.append("Historical incidents indicate repeated DB pressure pattern.")
            if step.action == "xuelang_change_lookup":
                evidence.append("Recent deployment changes happened before incident window.")
            if step.action == "rag_case_search":
                if observation.get("ok"):
                    evidence.append("RAG MCP returned similar historical diagnosis cases.")
                else:
                    evidence.append("RAG MCP query failed; diagnosis based on other tools.")

        top1 = "DB slow SQL and recent release change jointly caused connection pool exhaustion"
        suggestions = [
            "Check slow SQL top-N and execution plans immediately.",
            "Verify release diff around incident window and rollback risky change if needed.",
            "Scale DB connection pool and apply temporary traffic throttling.",
        ]
        return {
            "incident_id": incident.get("incident_id", ""),
            "root_cause_top1": top1,
            "root_cause_candidates": [
                {"cause": top1, "confidence": 0.84},
                {
                    "cause": "Upstream network jitter amplified timeout rate and retry storms",
                    "confidence": 0.61,
                },
            ],
            "evidence": evidence,
            "suggestions": suggestions,
            "confidence": 0.84,
        }


class ReActAgent:
    """经典 ReAct 循环执行器。"""

    def __init__(self, tools: list[Tool], max_steps: int = 6) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.planner = MockOpsPlanner()

    def run(self, incident: dict[str, Any]) -> DiagnosisResult:
        """执行 ReAct 循环。"""
        steps: list[ToolTraceStep] = []

        for idx in range(self.max_steps):
            action = self.planner.next_action(PlannerContext(incident=incident, steps=steps))
            if action.kind == "final":
                return self._to_result(action.final_payload, steps)

            if not action.function_call:
                # Planner 输出异常时，记录轨迹并继续下一轮
                steps.append(
                    ToolTraceStep(
                        index=idx + 1,
                        thought=action.thought,
                        action="unknown",
                        observation={"ok": False, "error": "missing function call"},
                    )
                )
                continue

            tool_name = action.function_call.name
            tool = self.tools.get(tool_name)
            if not tool:
                observation = {"ok": False, "error": f"tool not found: {tool_name}"}
            else:
                try:
                    observation = tool.run(action.function_call.arguments)
                    observation["ok"] = True
                except Exception as exc:  # noqa: BLE001
                    # tool 调用失败不直接抛异常，交给后续推理使用兜底证据
                    observation = {"ok": False, "error": str(exc)}

            steps.append(
                ToolTraceStep(
                    index=idx + 1,
                    thought=action.thought,
                    action=tool_name,
                    action_input=action.function_call.arguments,
                    observation=observation,
                )
            )

        return DiagnosisResult(
            incident_id=incident.get("incident_id", ""),
            root_cause_top1="Insufficient evidence due to max step limit",
            root_cause_candidates=[
                RootCauseCandidate(cause="Insufficient evidence due to max step limit", confidence=0.3)
            ],
            evidence=["ReAct max steps reached"],
            suggestions=["Escalate to on-call engineer for manual triage."],
            confidence=0.3,
            tool_trace=steps,
            result_json={"fallback": True},
        )

    def _to_result(self, payload: dict[str, Any], steps: list[ToolTraceStep]) -> DiagnosisResult:
        """将 planner 输出字典标准化为 DiagnosisResult。"""
        candidates = [
            RootCauseCandidate(cause=item["cause"], confidence=float(item["confidence"]))
            for item in payload.get("root_cause_candidates", [])
        ]
        if not candidates:
            candidates = [
                RootCauseCandidate(cause=str(payload.get("root_cause_top1", "unknown")), confidence=0.5)
            ]
        return DiagnosisResult(
            incident_id=str(payload.get("incident_id", "")),
            root_cause_top1=str(payload.get("root_cause_top1", candidates[0].cause)),
            root_cause_candidates=candidates,
            evidence=[str(x) for x in payload.get("evidence", [])],
            suggestions=[str(x) for x in payload.get("suggestions", [])],
            confidence=float(payload.get("confidence", candidates[0].confidence)),
            tool_trace=steps,
            result_json=payload,
        )
