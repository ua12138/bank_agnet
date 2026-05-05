"""
project_demo.py

这个 demo 不是基础 Python 三层架构示例。
它专门演示 Worker / Workflow / Agent 主链路：
1. incident payload 长什么样
2. task 如何从 NEW -> PROCESSING
3. payload validate 在哪里发生
4. workflow state 如何初始化
5. conditional branch 如何决定 approval / diagnose
6. agent 如何追加 tool_trace
7. 结果如何 save / notify / mark_done
"""

from dataclasses import dataclass, field
from typing import Literal

@dataclass
class IncidentPayload:
    incident_id: str
    system: str
    service: str
    severity: str
    hosts: list[str]
    metrics: list[str]
    need_approval: bool

@dataclass
class DiagnosisTask:
    task_id: int
    payload_json: dict
    status: str = "NEW"
    notify_status: str = "PENDING"

@dataclass
class WorkflowState:
    incident_id: str
    approval_status: str
    dedup_hit: bool
    tool_trace: list[dict] = field(default_factory=list)
    root_cause_top1: str = ""

def validate_payload(payload_json: dict) -> IncidentPayload:
    required = ["incident_id","system","service","severity","hosts","metrics","need_approval"]
    for key in required:
        if key not in payload_json:
            raise ValueError(f"payload 缺少字段: {key}")
    return IncidentPayload(**payload_json)

def claim_next_task(tasks: list[DiagnosisTask]) -> DiagnosisTask | None:
    for task in tasks:
        if task.status == "NEW":
            task.status = "PROCESSING"
            return task
    return None

def build_initial_state(payload: IncidentPayload) -> WorkflowState:
    return WorkflowState(
        incident_id=payload.incident_id,
        approval_status="pending" if payload.need_approval else "auto_approved",
        dedup_hit=False,
    )

def dedup_node(state: WorkflowState) -> WorkflowState:
    state.tool_trace.append({"node": "dedup", "observation": {"dedup_hit": False}})
    return state

def route_after_dedup(state: WorkflowState) -> Literal["approval", "diagnose"]:
    return "approval" if state.approval_status == "pending" else "diagnose"

def approval_node(state: WorkflowState) -> WorkflowState:
    state.root_cause_top1 = "Waiting for human approval"
    return state

def diagnose_node(state: WorkflowState) -> WorkflowState:
    state.tool_trace.append({"action": "metrics_lookup", "observation": {"cpu": 92, "mysql_conn": 188}})
    state.tool_trace.append({"action": "change_lookup", "observation": {"recent_release": "payment-api-v2.3.1"}})
    state.tool_trace.append({"action": "rag_case_search", "observation": {"matched_case": "connection_pool_exhaustion"}})
    state.root_cause_top1 = "DB slow SQL and recent release change jointly caused connection pool exhaustion"
    return state

def execute_workflow(payload: IncidentPayload) -> WorkflowState:
    state = build_initial_state(payload)
    state = dedup_node(state)
    if route_after_dedup(state) == "approval":
        state = approval_node(state)
    else:
        state = diagnose_node(state)
    return state

def save_result(task: DiagnosisTask, state: WorkflowState) -> dict:
    return {
        "task_id": task.task_id,
        "incident_id": state.incident_id,
        "status": "DONE",
        "notify_status": task.notify_status,
        "root_cause_top1": state.root_cause_top1,
        "tool_trace": state.tool_trace,
    }

def notify(task: DiagnosisTask, result: dict) -> None:
    task.notify_status = "SENT"
    print("[notify]", result["incident_id"])

def mark_done(task: DiagnosisTask) -> None:
    task.status = "DONE"

def process_one_task(tasks: list[DiagnosisTask]) -> dict | None:
    task = claim_next_task(tasks)
    if not task:
        return None
    payload = validate_payload(task.payload_json)
    state = execute_workflow(payload)
    result = save_result(task, state)
    notify(task, result)
    mark_done(task)
    result["notify_status"] = task.notify_status
    return result

if __name__ == "__main__":
    tasks = [DiagnosisTask(
        task_id=12,
        payload_json={
            "incident_id": "inc_20250801_001",
            "system": "payment-system",
            "service": "payment-api",
            "severity": "high",
            "hosts": ["db-prod-01", "api-prod-01"],
            "metrics": ["mysql.connections", "api.timeout.rate"],
            "need_approval": False,
        },
    )]
    print(process_one_task(tasks))
