from __future__ import annotations

"""demotest 最小化 API 入口。

用于验证 sqlite task -> pseudo worker -> pseudo react -> rag mcp 调用链路。
"""

from functools import lru_cache
from typing import Any

from fastapi import FastAPI

from demotest.app.db import DemoSQLite
from demotest.app.react_tools import PseudoReActEngine
from demotest.app.settings import get_demo_settings
from demotest.app.worker import DemoWorker


app = FastAPI(title="HZ AIOps DemoTest", version="1.0.0")


@lru_cache(maxsize=1)
def get_db() -> DemoSQLite:
    """初始化并缓存 demo sqlite。"""
    settings = get_demo_settings()
    db = DemoSQLite(settings.sqlite_path_obj)
    db.init()
    return db


@lru_cache(maxsize=1)
def get_worker() -> DemoWorker:
    """初始化并缓存 demo worker。"""
    settings = get_demo_settings()
    db = get_db()
    engine = PseudoReActEngine(
        rag_mcp_base_url=settings.rag_mcp_base_url,
        rag_timeout_sec=settings.rag_timeout_sec,
        rag_query_top_k=settings.rag_query_top_k,
        rag_candidate_multiplier=settings.rag_candidate_multiplier,
        rag_fast_mode=settings.rag_fast_mode,
        rag_use_memory=settings.rag_use_memory,
    )
    return DemoWorker(db=db, engine=engine)


def _sample_incident() -> dict[str, Any]:
    """构造一条固定伪数据，便于快速复现实验。"""
    return {
        "incident_id": "demo_inc_001",
        "system": "payment-system",
        "service": "payment-api",
        "severity": "high",
        "window_start": "2025-08-01T10:10:00Z",
        "window_end": "2025-08-01T10:15:00Z",
        "hosts": ["db-prod-01", "api-prod-01"],
        "metrics": [
            {"metric": "mysql.connections", "value": 980},
            {"metric": "api.timeout.rate", "value": 6.7},
        ],
        "recent_change_ids": ["chg_1001"],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    """返回 demotest 关键运行参数。"""
    settings = get_demo_settings()
    return {
        "ok": True,
        "sqlite_path": str(settings.sqlite_path_obj),
        "rag_mcp_base_url": settings.rag_mcp_base_url,
        "rag_timeout_sec": settings.rag_timeout_sec,
        "rag_query_top_k": settings.rag_query_top_k,
        "rag_candidate_multiplier": settings.rag_candidate_multiplier,
        "rag_fast_mode": settings.rag_fast_mode,
        "rag_use_memory": settings.rag_use_memory,
    }


@app.post("/demo/seed")
def seed() -> dict[str, Any]:
    """插入一条伪 incident 任务。"""
    task_id = get_db().insert_task(_sample_incident())
    return {"ok": True, "task_id": task_id}


@app.post("/demo/run-once")
def run_once() -> dict[str, Any]:
    """触发 worker 消费一次。"""
    return get_worker().run_once()


@app.get("/demo/tasks")
def list_tasks() -> list[dict[str, Any]]:
    """查看 demo 任务表。"""
    return get_db().list_tasks()


@app.get("/demo/results")
def list_results() -> list[dict[str, Any]]:
    """查看 demo 结果表。"""
    return get_db().list_results()


def run() -> None:
    """本地启动入口。"""
    import uvicorn

    uvicorn.run("demotest.app.main:app", host="0.0.0.0", port=8098, reload=False)


if __name__ == "__main__":
    run()
