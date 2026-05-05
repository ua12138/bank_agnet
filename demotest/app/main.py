"""模块说明：该文件用于承载项目中的相关实现。"""

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
    """get_db：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    settings = get_demo_settings()
    db = DemoSQLite(settings.sqlite_path_obj)
    db.init()
    return db


@lru_cache(maxsize=1)
def get_worker() -> DemoWorker:
    """get_worker：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
    """_sample_incident：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
    """health：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
    """seed：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    task_id = get_db().insert_task(_sample_incident())
    return {"ok": True, "task_id": task_id}


@app.post("/demo/run-once")
def run_once() -> dict[str, Any]:
    """run_once：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return get_worker().run_once()


@app.get("/demo/tasks")
def list_tasks() -> list[dict[str, Any]]:
    """list_tasks：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return get_db().list_tasks()


@app.get("/demo/results")
def list_results() -> list[dict[str, Any]]:
    """list_results：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return get_db().list_results()


def run() -> None:
    """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    import uvicorn

    uvicorn.run("demotest.app.main:app", host="0.0.0.0", port=8098, reload=False)


if __name__ == "__main__":
    run()
