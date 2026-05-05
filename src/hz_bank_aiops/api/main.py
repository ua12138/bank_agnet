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
    """提交 incident 请求体。"""

    incident: IncidentPayload
    priority: str = "P2"


class ApprovalSubmitRequest(BaseModel):
    """审批请求体（当前保留，接口使用 ApprovalDecisionRequest）。"""

    status: ApprovalStatus
    approver: str
    comment: str = ""


app = FastAPI(
    title="HZ Bank AIOps Incident Diagnosis API",
    version="1.0.0",
)


@lru_cache(maxsize=1)
def get_runtime() -> DiagnosisRuntime:
    """构建并缓存运行时单例。"""
    runtime = DiagnosisRuntime(get_settings())
    runtime.init_schema()
    return runtime


@app.get("/health")
def health() -> dict[str, Any]:
    """系统健康检查。"""
    return get_runtime().health()


@app.post("/api/v1/incidents")
def submit_incident(payload: IncidentSubmitRequest) -> dict[str, Any]:
    """提交 incident 并生成诊断任务。"""
    runtime = get_runtime()
    task_id = runtime.submit_incident(payload.incident, priority=payload.priority)
    return {"ok": True, "task_id": task_id, "incident_id": payload.incident.incident_id}


@app.get("/api/v1/tasks")
def list_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """查询最近任务列表。"""
    runtime = get_runtime()
    return [task.model_dump(mode="json") for task in runtime.list_tasks(limit=limit)]


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, Any]:
    """查询单个任务。"""
    runtime = get_runtime()
    task = runtime.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task.model_dump(mode="json")


@app.post("/api/v1/workers/run-once")
def run_worker_once(worker_id: str | None = None) -> dict[str, Any]:
    """触发 worker 单次处理，便于联调。"""
    runtime = get_runtime()
    wid = worker_id or get_settings().worker_id
    runner = WorkerRunner(runtime=runtime, worker_id=wid, poll_interval_sec=0.1)
    return runner.run_once()


@app.get("/api/v1/approvals/{incident_id}")
def get_approval(incident_id: str) -> dict[str, Any]:
    """读取 incident 审批状态。"""
    runtime = get_runtime()
    row = runtime.get_approval(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval not found")
    return row.model_dump(mode="json")


@app.post("/api/v1/approvals/{incident_id}")
def submit_approval(incident_id: str, payload: ApprovalDecisionRequest) -> dict[str, Any]:
    """提交人工审批结果。"""
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
    """RAG MCP 健康探测代理接口。"""
    return get_runtime().rag_client.health().__dict__


def run() -> None:
    """本地启动入口。"""
    import uvicorn

    uvicorn.run("hz_bank_aiops.api.main:app", host="0.0.0.0", port=8088, reload=False)


if __name__ == "__main__":
    run()
