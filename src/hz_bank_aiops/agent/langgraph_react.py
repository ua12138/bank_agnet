"""???????????????????"""

from __future__ import annotations

"""LangGraph 版 ReAct 执行器。

在原有 plan -> act -> observe 循环上，新增两项能力：
1. 滑动上下文窗口：planner 每轮只看最近 N 步。
2. 动态摘要记忆：超出窗口的历史步骤会被压缩进 summary，继续参与后续推理。
"""

import json
from typing import Any, TypedDict

from hz_bank_aiops.agent.react_agent import PlannerContext, ReActAgent
from hz_bank_aiops.models import DiagnosisResult, ToolTraceStep


class LangGraphReactUnavailableError(RuntimeError):
    """langgraph 依赖缺失时抛出。"""


class _ReActState(TypedDict, total=False):
    """_ReActState???????????????????"""
    incident: dict[str, Any]
    # 滑动窗口步骤，仅供 planner 使用
    steps: list[ToolTraceStep]
    # 完整步骤，供最终结果输出
    all_steps: list[ToolTraceStep]
    final_payload: dict[str, Any]
    next_tool: str
    next_input: dict[str, Any]
    thought: str
    done: bool
    cot_trace: list[str]
    # 动态摘要记忆
    memory_summary: str
    memory_snapshots: list[str]


class LangGraphReActExecutor:
    """LangGraph ReAct 执行器。"""

    def __init__(
        self,
        agent: ReActAgent,
        max_steps: int = 6,
        cot_enabled: bool = False,
        cot_max_chars: int = 240,
        cot_max_entries: int = 16,
        memory_enabled: bool = True,
        context_window_steps: int = 3,
        summary_max_chars: int = 480,
        summary_max_entries: int = 12,
    ) -> None:
        """????????????????????"""
        self.agent = agent
        self.max_steps = max_steps

        self.cot_enabled = cot_enabled
        self.cot_max_chars = max(80, cot_max_chars)
        self.cot_max_entries = max(4, cot_max_entries)

        self.memory_enabled = memory_enabled
        self.context_window_steps = max(1, context_window_steps)
        self.summary_max_chars = max(120, summary_max_chars)
        self.summary_max_entries = max(4, summary_max_entries)

        self.graph = self._build_graph()

    def _build_graph(self):
        """_build_graph??????????????????????????"""
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise LangGraphReactUnavailableError(
                "langgraph is required for LangGraphReActExecutor"
            ) from exc

        def plan(state: _ReActState) -> _ReActState:
            """plan??????????????????????????"""
            window_steps = list(state.get("steps", []))
            all_steps = list(state.get("all_steps", []))
            cot_trace = list(state.get("cot_trace", []))
            memory_summary = state.get("memory_summary", "")

            action = self.agent.planner.next_action(
                PlannerContext(
                    incident=state["incident"],
                    steps=window_steps,
                    completed_actions={step.action for step in all_steps},
                    memory_summary=memory_summary,
                )
            )

            step_no = len(all_steps) + 1
            if action.kind == "final":
                if self.cot_enabled:
                    cot_trace = self._append_cot(
                        cot_trace,
                        f"Step {step_no} - conclude: {self._clip(action.thought)}",
                    )
                return {
                    "final_payload": action.final_payload,
                    "thought": action.thought,
                    "done": True,
                    "cot_trace": cot_trace,
                }

            if not action.function_call:
                if self.cot_enabled:
                    cot_trace = self._append_cot(
                        cot_trace,
                        f"Step {step_no} - conclude: missing function call, stop loop.",
                    )
                return {
                    "done": True,
                    "final_payload": {"incident_id": state["incident"].get("incident_id", "")},
                    "cot_trace": cot_trace,
                }

            if self.cot_enabled:
                plan_line = (
                    f"Step {step_no} - plan: {self._clip(action.thought)} -> call {action.function_call.name}"
                )
                if self.memory_enabled and memory_summary:
                    plan_line = f"{plan_line} | memory=on"
                cot_trace = self._append_cot(cot_trace, plan_line)

            return {
                "next_tool": action.function_call.name,
                "next_input": action.function_call.arguments,
                "thought": action.thought,
                "done": False,
                "cot_trace": cot_trace,
            }

        def act(state: _ReActState) -> _ReActState:
            """act??????????????????????????"""
            window_steps = list(state.get("steps", []))
            all_steps = list(state.get("all_steps", []))
            cot_trace = list(state.get("cot_trace", []))
            memory_summary = state.get("memory_summary", "")
            memory_snapshots = list(state.get("memory_snapshots", []))

            idx = len(all_steps) + 1
            tool_name = state.get("next_tool", "")
            action_input = state.get("next_input", {})
            tool = self.agent.tools.get(tool_name)
            if not tool:
                observation = {"ok": False, "error": f"tool not found: {tool_name}"}
            else:
                try:
                    observation = tool.run(action_input)
                    observation["ok"] = True
                except Exception as exc:  # noqa: BLE001
                    observation = {"ok": False, "error": str(exc)}

            step = ToolTraceStep(
                index=idx,
                thought=state.get("thought", ""),
                action=tool_name,
                action_input=action_input,
                observation=observation,
            )
            all_steps.append(step)
            window_steps.append(step)

            if self.memory_enabled and len(window_steps) > self.context_window_steps:
                overflow = len(window_steps) - self.context_window_steps
                overflow_steps = window_steps[:overflow]
                window_steps = window_steps[overflow:]
                memory_summary = self._merge_summary(memory_summary, overflow_steps)
                if memory_summary:
                    memory_snapshots.append(memory_summary)
                    if len(memory_snapshots) > self.summary_max_entries:
                        memory_snapshots = memory_snapshots[-self.summary_max_entries :]
                if self.cot_enabled:
                    cot_trace = self._append_cot(
                        cot_trace,
                        (
                            f"Step {idx} - memory_update: summarized {len(overflow_steps)} old steps, "
                            f"window={len(window_steps)}"
                        ),
                    )

            if self.cot_enabled:
                cot_trace = self._append_cot(
                    cot_trace,
                    f"Step {idx} - observe({tool_name}): {self._compact_observation(observation)}",
                )

            done = idx >= self.max_steps
            return {
                "steps": window_steps,
                "all_steps": all_steps,
                "done": done,
                "cot_trace": cot_trace,
                "memory_summary": memory_summary,
                "memory_snapshots": memory_snapshots,
            }

        def route_after_plan(state: _ReActState) -> str:
            """route_after_plan??????????????????????????"""
            return "end" if state.get("done", False) else "act"

        def route_after_act(state: _ReActState) -> str:
            """route_after_act??????????????????????????"""
            return "plan" if not state.get("done", False) else "end"

        graph = StateGraph(_ReActState)
        graph.add_node("plan", plan)
        graph.add_node("act", act)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", route_after_plan, {"act": "act", "end": END})
        graph.add_conditional_edges("act", route_after_act, {"plan": "plan", "end": END})
        return graph.compile()

    def run(self, incident: dict[str, Any]) -> DiagnosisResult:
        """run??????????????????????????"""
        result = self.graph.invoke(
            {
                "incident": incident,
                "steps": [],
                "all_steps": [],
                "done": False,
                "cot_trace": [],
                "memory_summary": "",
                "memory_snapshots": [],
            }
        )
        final_payload = result.get("final_payload", {})
        all_steps = result.get("all_steps", [])
        diagnosis = self.agent._to_result(final_payload, all_steps)  # noqa: SLF001

        if self.cot_enabled:
            diagnosis.result_json["cot"] = {
                "enabled": True,
                "trace": result.get("cot_trace", []),
            }

        diagnosis.result_json["context_memory"] = {
            "enabled": self.memory_enabled,
            "window_steps": self.context_window_steps,
            "window_step_count": len(result.get("steps", [])),
            "all_step_count": len(all_steps),
            "summary": result.get("memory_summary", ""),
            "summary_snapshots": result.get("memory_snapshots", []),
        }
        return diagnosis

    def _merge_summary(self, existing: str, overflow_steps: list[ToolTraceStep]) -> str:
        """_merge_summary??????????????????????????"""
        lines = [line for line in existing.split("\n") if line.strip()] if existing else []
        for step in overflow_steps:
            status = "ok" if step.observation.get("ok") else "error"
            line = (
                f"Step {step.index} {step.action} [{status}] "
                f"{self._compact_observation(step.observation)}"
            )
            lines.append(self._clip_summary_line(line))

        if len(lines) > self.summary_max_entries:
            lines = lines[-self.summary_max_entries :]

        merged = "\n".join(lines)
        return self._clip_with_limit(merged, self.summary_max_chars)

    def _append_cot(self, cot_trace: list[str], line: str) -> list[str]:
        """_append_cot??????????????????????????"""
        cot_trace.append(self._clip(line))
        if len(cot_trace) > self.cot_max_entries:
            return cot_trace[-self.cot_max_entries :]
        return cot_trace

    def _clip(self, text: str) -> str:
        """_clip??????????????????????????"""
        if len(text) <= self.cot_max_chars:
            return text
        return text[: self.cot_max_chars - 3] + "..."

    def _clip_with_limit(self, text: str, max_chars: int) -> str:
        """_clip_with_limit??????????????????????????"""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _clip_summary_line(self, text: str) -> str:
        """_clip_summary_line??????????????????????????"""
        line_limit = max(120, self.summary_max_chars // 2)
        return self._clip_with_limit(text, line_limit)

    def _compact_observation(self, observation: dict[str, Any]) -> str:
        """_compact_observation??????????????????????????"""
        if not observation:
            return "empty observation"
        if observation.get("ok") is False and observation.get("error"):
            return self._clip(f"error={observation.get('error', '')}")

        compact = dict(observation)
        for key in ("metrics_snapshot", "historical_incidents", "recent_changes"):
            values = compact.get(key)
            if isinstance(values, list) and len(values) > 1:
                compact[key] = values[:1]
                compact[f"{key}_count"] = len(values)
        compact_text = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
        return self._clip(compact_text)
