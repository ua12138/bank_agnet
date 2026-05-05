"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""demotest sqlite 存储层。"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


class DemoSQLite:
    """DemoSQLite：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, path: Path) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        """conn：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        """init：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        with self.conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    reasoning_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def insert_task(self, payload: dict) -> int:
        """insert_task：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        now = datetime.now(UTC).isoformat()
        with self.conn() as c:
            cur = c.execute(
                """
                INSERT INTO task(incident_id, payload_json, status, created_at, updated_at)
                VALUES (?, ?, 'NEW', ?, ?)
                """,
                (payload["incident_id"], json.dumps(payload, ensure_ascii=False), now, now),
            )
            return int(cur.lastrowid)

    def claim_task(self) -> sqlite3.Row | None:
        """claim_task：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        now = datetime.now(UTC).isoformat()
        with self.conn() as c:
            row = c.execute(
                "SELECT * FROM task WHERE status='NEW' ORDER BY id ASC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            c.execute("UPDATE task SET status='PROCESSING', updated_at=? WHERE id=?", (now, row["id"]))
            return row

    def mark_done(self, task_id: int) -> None:
        """mark_done：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        now = datetime.now(UTC).isoformat()
        with self.conn() as c:
            c.execute("UPDATE task SET status='DONE', updated_at=? WHERE id=?", (now, task_id))

    def save_result(self, incident_id: str, summary: str, reasoning: list[dict]) -> int:
        """save_result：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        now = datetime.now(UTC).isoformat()
        with self.conn() as c:
            cur = c.execute(
                """
                INSERT INTO result(incident_id, summary, reasoning_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (incident_id, summary, json.dumps(reasoning, ensure_ascii=False), now),
            )
            return int(cur.lastrowid)

    def list_tasks(self) -> list[dict]:
        """list_tasks：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        with self.conn() as c:
            rows = c.execute("SELECT * FROM task ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    def list_results(self) -> list[dict]:
        """list_results：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        with self.conn() as c:
            rows = c.execute("SELECT * FROM result ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]
