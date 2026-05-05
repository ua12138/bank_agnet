from __future__ import annotations

"""demotest sqlite 存储层。"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


class DemoSQLite:
    """demo 任务表/结果表访问对象。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        """sqlite 连接上下文。"""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        """初始化 demo 表结构。"""
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
        """插入一条待处理任务。"""
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
        """抢占最早 NEW 任务并更新为 PROCESSING。"""
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
        """标记任务完成。"""
        now = datetime.now(UTC).isoformat()
        with self.conn() as c:
            c.execute("UPDATE task SET status='DONE', updated_at=? WHERE id=?", (now, task_id))

    def save_result(self, incident_id: str, summary: str, reasoning: list[dict]) -> int:
        """保存 pseudo ReAct 结果。"""
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
        """查看任务表。"""
        with self.conn() as c:
            rows = c.execute("SELECT * FROM task ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    def list_results(self) -> list[dict]:
        """查看结果表。"""
        with self.conn() as c:
            rows = c.execute("SELECT * FROM result ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]
