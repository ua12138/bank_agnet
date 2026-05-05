"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""经典 ReAct Agent 实现（无外部 LLM 依赖的可运行版本）。"""

from dataclasses import dataclass
import json
from typing import Any

import httpx
from pydantic import BaseModel, Field

from hz_bank_aiops.models import DiagnosisResult, RootCauseCandidate, ToolTraceStep
from hz_bank_aiops.tools import Tool


class FunctionCall(BaseModel):
    """FunctionCall：封装该领域职责，供上层流程统一调用。"""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMAction(BaseModel):
    """LLMAction：封装该领域职责，供上层流程统一调用。"""

    kind: str  # "tool" | "final"
    thought: str
    function_call: FunctionCall | None = None
    final_payload: dict[str, Any] = Field(default_factory=dict)


@dataclass
class PlannerContext:
    """PlannerContext：封装该领域职责，供上层流程统一调用。"""

    incident: dict[str, Any]
    steps: list[ToolTraceStep]
    completed_actions: set[str] | None = None
    memory_summary: str = ""


class MockOpsPlanner:
    """MockOpsPlanner：封装该领域职责，供上层流程统一调用。"""

    sequence = [
        "zabbix_realtime_metrics",
        "doris_history_lookup",
        "xuelang_change_lookup",
        "rag_case_search",
    ]

    def next_action(self, ctx: PlannerContext) -> LLMAction:
        """next_action：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
        """_build_final：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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


class SiliconFlowPlanner:
    """SiliconFlowPlanner：封装该领域职责，供上层流程统一调用。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_sec: float,
        fallback_planner: MockOpsPlanner | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec
        self.fallback_planner = fallback_planner or MockOpsPlanner()

    def next_action(self, ctx: PlannerContext) -> LLMAction:
        """next_action：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if not self.api_key:
            return self.fallback_planner.next_action(ctx)

        try:
            return self._next_action_by_llm(ctx)
        except Exception:  # noqa: BLE001
            return self.fallback_planner.next_action(ctx)

    def _next_action_by_llm(self, ctx: PlannerContext) -> LLMAction:
        steps_summary = [
            {
                "index": step.index,
                "action": step.action,
                "ok": bool(step.observation.get("ok")),
                "error": str(step.observation.get("error", ""))[:200],
            }
            for step in ctx.steps
        ]
        completed_actions = sorted(ctx.completed_actions or set())

        schema_tip = {
            "kind": "tool|final",
            "thought": "string",
            "function_call": {"name": "tool_name", "arguments": {"incident": "<incident object>"}},
            "final_payload": {
                "incident_id": "string",
                "root_cause_top1": "string",
                "root_cause_candidates": [{"cause": "string", "confidence": 0.0}],
                "evidence": ["string"],
                "suggestions": ["string"],
                "confidence": 0.0,
            },
        }
        prompt = (
            "You are an AIOps ReAct planner. Decide next action.\n"
            "Output JSON only, no markdown.\n"
            f"Output schema example: {json.dumps(schema_tip, ensure_ascii=False)}\n"
            f"Incident: {json.dumps(ctx.incident, ensure_ascii=False)}\n"
            f"Recent steps: {json.dumps(steps_summary, ensure_ascii=False)}\n"
            f"Completed actions: {json.dumps(completed_actions, ensure_ascii=False)}\n"
            f"Memory summary: {ctx.memory_summary}\n"
            "If more evidence is needed, return kind=tool and choose one of: "
            "zabbix_realtime_metrics, doris_history_lookup, xuelang_change_lookup, rag_case_search. "
            "If enough evidence, return kind=final with concise payload."
        )

        with httpx.Client(timeout=self.timeout_sec) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a strict JSON generator."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

        parsed = json.loads(content)
        kind = str(parsed.get("kind", "")).strip().lower()
        thought = str(parsed.get("thought", ""))
        if kind == "tool":
            fc = parsed.get("function_call") or {}
            tool_name = str(fc.get("name", ""))
            arguments = fc.get("arguments") or {"incident": ctx.incident}
            if tool_name not in MockOpsPlanner.sequence:
                return self.fallback_planner.next_action(ctx)
            return LLMAction(
                kind="tool",
                thought=thought or f"Need more evidence from {tool_name}.",
                function_call=FunctionCall(name=tool_name, arguments=arguments),
            )

        if kind == "final":
            payload = parsed.get("final_payload") or {}
            payload.setdefault("incident_id", ctx.incident.get("incident_id", ""))
            return LLMAction(kind="final", thought=thought or "Generate final diagnosis.", final_payload=payload)

        return self.fallback_planner.next_action(ctx)


class ReActAgent:
    """ReActAgent：封装该领域职责，供上层流程统一调用。"""

    def __init__(
        self,
        tools: list[Tool],
        max_steps: int = 6,
        llm_provider: str = "siliconflow",
        llm_api_key: str = "",
        llm_base_url: str = "https://api.siliconflow.cn/v1",
        llm_model: str = "Qwen/Qwen2.5-14B-Instruct",
        llm_request_timeout_sec: float = 20.0,
    ) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.fallback_planner = MockOpsPlanner()
        if llm_provider == "siliconflow" and llm_api_key:
            self.planner = SiliconFlowPlanner(
                api_key=llm_api_key,
                base_url=llm_base_url,
                model=llm_model,
                timeout_sec=llm_request_timeout_sec,
                fallback_planner=self.fallback_planner,
            )
            self.planner_mode = "siliconflow"
        else:
            self.planner = self.fallback_planner
            self.planner_mode = "mock"

    def run(self, incident: dict[str, Any]) -> DiagnosisResult:
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
        """_to_result：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
