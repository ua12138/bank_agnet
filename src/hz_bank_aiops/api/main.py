"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""FastAPI 服务入口。"""

from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from hz_bank_aiops.config import get_settings
from hz_bank_aiops.models import ApprovalDecisionRequest, ApprovalStatus, IncidentPayload
from hz_bank_aiops.service import DiagnosisRuntime
from hz_bank_aiops.worker import WorkerRunner


class IncidentSubmitRequest(BaseModel):
    """IncidentSubmitRequest：封装该领域职责，供上层流程统一调用。"""

    incident: IncidentPayload
    priority: str = "P2"


class ApprovalSubmitRequest(BaseModel):
    """ApprovalSubmitRequest：封装该领域职责，供上层流程统一调用。"""

    status: ApprovalStatus
    approver: str
    comment: str = ""


app = FastAPI(
    title="HZ Bank AIOps Incident Diagnosis API",
    version="1.0.0",
)


@lru_cache(maxsize=1)
def get_runtime() -> DiagnosisRuntime:
    """get_runtime：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = DiagnosisRuntime(get_settings())
    runtime.init_schema()
    return runtime


@app.get("/health")
def health() -> dict[str, Any]:
    """health：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return get_runtime().health()


@app.post("/api/v1/incidents")
def submit_incident(payload: IncidentSubmitRequest) -> dict[str, Any]:
    """submit_incident：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    task_id = runtime.submit_incident(payload.incident, priority=payload.priority)
    return {"ok": True, "task_id": task_id, "incident_id": payload.incident.incident_id}


@app.get("/api/v1/tasks")
def list_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """list_tasks：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    return [task.model_dump(mode="json") for task in runtime.list_tasks(limit=limit)]


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, Any]:
    """get_task：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    task = runtime.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task.model_dump(mode="json")


@app.post("/api/v1/workers/run-once")
def run_worker_once(worker_id: str | None = None) -> dict[str, Any]:
    """run_worker_once：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    wid = worker_id or get_settings().worker_id
    runner = WorkerRunner(runtime=runtime, worker_id=wid, poll_interval_sec=0.1)
    return runner.run_once()


@app.get("/api/v1/approvals/{incident_id}")
def get_approval(incident_id: str) -> dict[str, Any]:
    """get_approval：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    row = runtime.get_approval(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval not found")
    return row.model_dump(mode="json")


@app.post("/api/v1/approvals/{incident_id}")
def submit_approval(incident_id: str, payload: ApprovalDecisionRequest) -> dict[str, Any]:
    """submit_approval：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    runtime = get_runtime()
    if payload.status not in {ApprovalStatus.approved, ApprovalStatus.rejected}:
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    row = runtime.submit_approval(
        incident_id=incident_id,
        status=payload.status,
        approver=payload.approver,
        comment=payload.comment,
    )
    return row.model_dump(mode="json")


@app.get("/api/v1/rag/health")
def rag_health() -> dict[str, Any]:
    """rag_health：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return get_runtime().rag_client.health().__dict__


def run() -> None:
    """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    import uvicorn

    uvicorn.run("hz_bank_aiops.api.main:app", host="0.0.0.0", port=8088, reload=False)


if __name__ == "__main__":
    run()
