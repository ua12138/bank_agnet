"""????????? SQLite/PostgreSQL ??????????????"""

from __future__ import annotations

"""任务存储抽象与实现。

当前提供两套实现：
- SQLiteTaskStore：单机/开发环境，易用优先
- PostgresTaskStore：生产环境，多 worker 并发消费
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from hz_bank_aiops.models import (
    ApprovalRecord,
    ApprovalStatus,
    DiagnosisResult,
    DiagnosisTask,
    NotifyStatus,
    TaskClaimResult,
    TaskStatus,
)


def _utcnow_str() -> str:
    """统一生成 UTC 时间字符串。"""
    return datetime.now(UTC).isoformat()


def _priority_rank(priority: str) -> int:
    """将优先级映射为可排序的数值（数值越小优先级越高）。"""
    mapping = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return mapping.get(priority.upper(), 2)


class TaskStore(ABC):
    """任务存储统一接口。"""

    @abstractmethod
    def init_schema(self) -> None:
        """init_schema??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def enqueue_incident(self, payload: dict[str, Any], priority: str = "P2") -> int:
        """enqueue_incident??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def claim_next_task(self, worker_id: str) -> TaskClaimResult:
        """claim_next_task??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def mark_done(self, task_id: int, notify_status: NotifyStatus) -> None:
        """mark_done??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def mark_failed(self, task_id: int, error_message: str, retryable: bool) -> None:
        """mark_failed??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def save_result(self, result: DiagnosisResult) -> int:
        """save_result??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def get_task(self, task_id: int) -> DiagnosisTask | None:
        """get_task??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def list_tasks(self, limit: int = 50) -> list[DiagnosisTask]:
        """list_tasks??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def upsert_approval(self, record: ApprovalRecord) -> None:
        """upsert_approval??????????????????????????"""
        raise NotImplementedError

    @abstractmethod
    def get_approval(self, incident_id: str) -> ApprovalRecord | None:
        """get_approval??????????????????????????"""
        raise NotImplementedError


class SQLiteTaskStore(TaskStore):
    """基于 sqlite 的任务存储实现。"""

    def __init__(self, db_path: Path, max_retry_default: int = 3) -> None:
        """????????????????????"""
        self.db_path = db_path
        self.max_retry_default = max_retry_default
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """连接上下文管理：自动提交并关闭。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        """初始化任务表、结果表、审批表。"""
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS diagnosis_task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    system_name TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'P2',
                    priority_rank INTEGER NOT NULL DEFAULT 2,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retry INTEGER NOT NULL DEFAULT 3,
                    worker_id TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT NOT NULL DEFAULT '',
                    need_notify INTEGER NOT NULL DEFAULT 1,
                    notify_status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_status_pri_ctime
                ON diagnosis_task(status, priority_rank, created_at);

                CREATE TABLE IF NOT EXISTS diagnosis_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    root_cause_top1 TEXT NOT NULL,
                    root_cause_candidates_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    suggestions_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    llm_model TEXT NOT NULL,
                    tool_trace_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approval_record (
                    incident_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    approver TEXT NOT NULL DEFAULT '',
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def enqueue_incident(self, payload: dict[str, Any], priority: str = "P2") -> int:
        """入队一个 Incident。

        幂等策略：同一 incident_id 若已有 NEW/PROCESSING 任务则直接返回旧 task_id。
        """
        incident_id = str(payload.get("incident_id", ""))
        system_name = str(payload.get("system", "unknown-system"))
        service_name = str(payload.get("service", "unknown-service"))
        now = _utcnow_str()

        with self._conn() as conn:
            # Avoid duplicate active tasks for the same incident.
            active = conn.execute(
                """
                SELECT id FROM diagnosis_task
                WHERE incident_id = ? AND status IN ('NEW', 'PROCESSING')
                LIMIT 1
                """,
                (incident_id,),
            ).fetchone()
            if active:
                return int(active["id"])

            cur = conn.execute(
                """
                INSERT INTO diagnosis_task(
                    incident_id, system_name, service_name, priority, priority_rank, status,
                    payload_json, retry_count, max_retry, need_notify, notify_status,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'NEW', ?, 0, ?, 1, 'PENDING', ?, ?)
                """,
                (
                    incident_id,
                    system_name,
                    service_name,
                    priority,
                    _priority_rank(priority),
                    json.dumps(payload, ensure_ascii=False),
                    self.max_retry_default,
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def claim_next_task(self, worker_id: str) -> TaskClaimResult:
        """按优先级和创建时间抢占一条待处理任务。"""
        now = _utcnow_str()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM diagnosis_task
                WHERE status = 'NEW'
                ORDER BY priority_rank ASC, created_at ASC
                LIMIT 1
                """,
            ).fetchone()
            if not row:
                return TaskClaimResult(claimed=False, task=None)

            conn.execute(
                """
                UPDATE diagnosis_task
                SET status='PROCESSING', worker_id=?, started_at=?, updated_at=?
                WHERE id=?
                """,
                (worker_id, now, now, row["id"]),
            )
            row_dict = dict(row)
            row_dict["status"] = TaskStatus.processing.value
            row_dict["worker_id"] = worker_id
            row_dict["started_at"] = now
            row_dict["updated_at"] = now
            task = DiagnosisTask(
                id=int(row_dict["id"]),
                incident_id=row_dict["incident_id"],
                system_name=row_dict["system_name"],
                service_name=row_dict["service_name"],
                priority=row_dict["priority"],
                status=TaskStatus(row_dict["status"]),
                payload_json=json.loads(row_dict["payload_json"]),
                retry_count=int(row_dict["retry_count"]),
                max_retry=int(row_dict["max_retry"]),
                worker_id=row_dict["worker_id"] or None,
                started_at=datetime.fromisoformat(row_dict["started_at"]) if row_dict["started_at"] else None,
                finished_at=datetime.fromisoformat(row_dict["finished_at"]) if row_dict["finished_at"] else None,
                error_message=row_dict["error_message"] or "",
                need_notify=bool(row_dict["need_notify"]),
                notify_status=NotifyStatus(row_dict["notify_status"]),
                created_at=datetime.fromisoformat(row_dict["created_at"]),
                updated_at=datetime.fromisoformat(row_dict["updated_at"]),
            )
            return TaskClaimResult(claimed=True, task=task)

    def mark_done(self, task_id: int, notify_status: NotifyStatus) -> None:
        """标记任务完成，同时记录通知状态。"""
        now = _utcnow_str()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE diagnosis_task
                SET status='DONE', finished_at=?, notify_status=?, updated_at=?
                WHERE id=?
                """,
                (now, notify_status.value, now, task_id),
            )

    def mark_failed(self, task_id: int, error_message: str, retryable: bool) -> None:
        """标记任务失败，并按重试策略决定是否回到 NEW。"""
        now = _utcnow_str()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT retry_count, max_retry FROM diagnosis_task WHERE id=?",
                (task_id,),
            ).fetchone()
            if not row:
                return

            retry_count = int(row["retry_count"]) + 1
            max_retry = int(row["max_retry"])
            # 仅当允许重试且未超最大重试次数时，回到 NEW
            if retryable and retry_count < max_retry:
                status = TaskStatus.new.value
            else:
                status = TaskStatus.failed.value

            conn.execute(
                """
                UPDATE diagnosis_task
                SET status=?, retry_count=?, error_message=?, updated_at=?
                WHERE id=?
                """,
                (status, retry_count, error_message[:2000], now, task_id),
            )

    def save_result(self, result: DiagnosisResult) -> int:
        """落库诊断结果。"""
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO diagnosis_result(
                    incident_id, root_cause_top1, root_cause_candidates_json,
                    evidence_json, suggestions_json, confidence, llm_model,
                    tool_trace_json, result_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.incident_id,
                    result.root_cause_top1,
                    json.dumps(
                        [item.model_dump(mode="json") for item in result.root_cause_candidates],
                        ensure_ascii=False,
                    ),
                    json.dumps(result.evidence, ensure_ascii=False),
                    json.dumps(result.suggestions, ensure_ascii=False),
                    result.confidence,
                    result.llm_model,
                    json.dumps(
                        [item.model_dump(mode="json") for item in result.tool_trace],
                        ensure_ascii=False,
                    ),
                    json.dumps(result.result_json, ensure_ascii=False),
                    result.created_at.isoformat(),
                ),
            )
            return int(cur.lastrowid)

    def get_task(self, task_id: int) -> DiagnosisTask | None:
        """按 id 查询单个任务。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM diagnosis_task WHERE id=?",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_tasks(self, limit: int = 50) -> list[DiagnosisTask]:
        """按 id 倒序查询最近任务。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM diagnosis_task ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_task(row) for row in rows]

    def upsert_approval(self, record: ApprovalRecord) -> None:
        """插入或更新审批记录（incident_id 唯一）。"""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO approval_record(incident_id, status, approver, comment, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    status=excluded.status,
                    approver=excluded.approver,
                    comment=excluded.comment,
                    updated_at=excluded.updated_at
                """,
                (
                    record.incident_id,
                    record.status.value,
                    record.approver,
                    record.comment,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )

    def get_approval(self, incident_id: str) -> ApprovalRecord | None:
        """查询审批记录。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approval_record WHERE incident_id=?",
                (incident_id,),
            ).fetchone()
            if not row:
                return None
            return ApprovalRecord(
                incident_id=row["incident_id"],
                status=ApprovalStatus(row["status"]),
                approver=row["approver"],
                comment=row["comment"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def _row_to_task(self, row: sqlite3.Row) -> DiagnosisTask:
        """将数据库行转换为业务对象。"""
        return DiagnosisTask(
            id=int(row["id"]),
            incident_id=row["incident_id"],
            system_name=row["system_name"],
            service_name=row["service_name"],
            priority=row["priority"],
            status=TaskStatus(row["status"]),
            payload_json=json.loads(row["payload_json"]),
            retry_count=int(row["retry_count"]),
            max_retry=int(row["max_retry"]),
            worker_id=row["worker_id"] or None,
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            error_message=row["error_message"] or "",
            need_notify=bool(row["need_notify"]),
            notify_status=NotifyStatus(row["notify_status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class PostgresTaskStore(TaskStore):
    """
    Production-grade task store for PostgreSQL.
    Requires `psycopg` (v3).
    """

    def __init__(self, dsn: str, max_retry_default: int = 3) -> None:
        """????????????????????"""
        self.dsn = dsn
        self.max_retry_default = max_retry_default
        try:
            import psycopg  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("psycopg is required for PostgresTaskStore") from exc
        self._psycopg = psycopg

    @contextmanager
    def _conn(self):
        """postgres 连接上下文管理。"""
        conn = self._psycopg.connect(self.dsn, autocommit=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        """初始化 PostgreSQL 表结构。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS diagnosis_task (
                        id BIGSERIAL PRIMARY KEY,
                        incident_id VARCHAR(64) NOT NULL,
                        system_name VARCHAR(64) NOT NULL,
                        service_name VARCHAR(64),
                        priority VARCHAR(16) NOT NULL DEFAULT 'P2',
                        status VARCHAR(16) NOT NULL,
                        payload_json JSONB NOT NULL,
                        retry_count INT NOT NULL DEFAULT 0,
                        max_retry INT NOT NULL DEFAULT 3,
                        worker_id VARCHAR(64),
                        started_at TIMESTAMP,
                        finished_at TIMESTAMP,
                        error_message TEXT,
                        need_notify BOOLEAN NOT NULL DEFAULT TRUE,
                        notify_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_diagnosis_task_status_priority_created
                    ON diagnosis_task(status, priority, created_at);
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS diagnosis_result (
                        id BIGSERIAL PRIMARY KEY,
                        incident_id VARCHAR(64) NOT NULL,
                        root_cause_top1 TEXT,
                        root_cause_candidates JSONB,
                        evidence_json JSONB,
                        suggestions_json JSONB,
                        confidence NUMERIC(5,4),
                        llm_model VARCHAR(64),
                        tool_trace_json JSONB,
                        result_json JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS approval_record (
                        incident_id VARCHAR(64) PRIMARY KEY,
                        status VARCHAR(32) NOT NULL,
                        approver VARCHAR(128) NOT NULL DEFAULT '',
                        comment TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    """
                )

    def enqueue_incident(self, payload: dict[str, Any], priority: str = "P2") -> int:
        """入队一个 Incident（带活动任务幂等检查）。"""
        incident_id = str(payload.get("incident_id", ""))
        system_name = str(payload.get("system", "unknown-system"))
        service_name = str(payload.get("service", "unknown-service"))
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM diagnosis_task
                    WHERE incident_id=%s AND status IN ('NEW', 'PROCESSING')
                    LIMIT 1
                    """,
                    (incident_id,),
                )
                row = cur.fetchone()
                if row:
                    return int(row[0])
                cur.execute(
                    """
                    INSERT INTO diagnosis_task(
                        incident_id, system_name, service_name, priority, status, payload_json, max_retry
                    )
                    VALUES (%s, %s, %s, %s, 'NEW', %s, %s)
                    RETURNING id
                    """,
                    (incident_id, system_name, service_name, priority, json.dumps(payload), self.max_retry_default),
                )
                return int(cur.fetchone()[0])

    def claim_next_task(self, worker_id: str) -> TaskClaimResult:
        """并发安全抢占任务。

        使用 `FOR UPDATE SKIP LOCKED`，多 worker 可并行消费不同任务。
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH cte AS (
                        SELECT id
                        FROM diagnosis_task
                        WHERE status = 'NEW'
                        ORDER BY priority ASC, created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE diagnosis_task t
                    SET status='PROCESSING', worker_id=%s, started_at=NOW(), updated_at=NOW()
                    FROM cte
                    WHERE t.id = cte.id
                    RETURNING t.id
                    """,
                    (worker_id,),
                )
                row = cur.fetchone()
                if not row:
                    return TaskClaimResult(claimed=False, task=None)
                task = self.get_task(int(row[0]))
                return TaskClaimResult(claimed=True, task=task)

    def mark_done(self, task_id: int, notify_status: NotifyStatus) -> None:
        """标记任务完成。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE diagnosis_task
                    SET status='DONE', finished_at=NOW(), notify_status=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (notify_status.value, task_id),
                )

    def mark_failed(self, task_id: int, error_message: str, retryable: bool) -> None:
        """标记任务失败并执行重试判定。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT retry_count, max_retry FROM diagnosis_task WHERE id=%s",
                    (task_id,),
                )
                row = cur.fetchone()
                if not row:
                    return
                retry_count = int(row[0]) + 1
                max_retry = int(row[1])
                status = "NEW" if retryable and retry_count < max_retry else "FAILED"
                cur.execute(
                    """
                    UPDATE diagnosis_task
                    SET status=%s, retry_count=%s, error_message=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (status, retry_count, error_message[:2000], task_id),
                )

    def save_result(self, result: DiagnosisResult) -> int:
        """写入诊断结果。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO diagnosis_result(
                        incident_id, root_cause_top1, root_cause_candidates,
                        evidence_json, suggestions_json, confidence, llm_model, tool_trace_json, result_json
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb)
                    RETURNING id
                    """,
                    (
                        result.incident_id,
                        result.root_cause_top1,
                        json.dumps([item.model_dump(mode="json") for item in result.root_cause_candidates]),
                        json.dumps(result.evidence),
                        json.dumps(result.suggestions),
                        result.confidence,
                        result.llm_model,
                        json.dumps([item.model_dump(mode="json") for item in result.tool_trace]),
                        json.dumps(result.result_json),
                    ),
                )
                return int(cur.fetchone()[0])

    def get_task(self, task_id: int) -> DiagnosisTask | None:
        """查询单个任务。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, incident_id, system_name, COALESCE(service_name, ''), priority, status,
                           payload_json::text, retry_count, max_retry, COALESCE(worker_id, ''),
                           started_at, finished_at, COALESCE(error_message, ''), need_notify, notify_status,
                           created_at, updated_at
                    FROM diagnosis_task
                    WHERE id=%s
                    """,
                    (task_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return DiagnosisTask(
                    id=int(row[0]),
                    incident_id=row[1],
                    system_name=row[2],
                    service_name=row[3],
                    priority=row[4],
                    status=TaskStatus(row[5]),
                    payload_json=json.loads(row[6]),
                    retry_count=int(row[7]),
                    max_retry=int(row[8]),
                    worker_id=row[9] or None,
                    started_at=row[10],
                    finished_at=row[11],
                    error_message=row[12],
                    need_notify=bool(row[13]),
                    notify_status=NotifyStatus(row[14]),
                    created_at=row[15].replace(tzinfo=UTC),
                    updated_at=row[16].replace(tzinfo=UTC),
                )

    def list_tasks(self, limit: int = 50) -> list[DiagnosisTask]:
        """查询最近任务列表。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM diagnosis_task
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                ids = [int(row[0]) for row in cur.fetchall()]
        tasks: list[DiagnosisTask] = []
        for task_id in ids:
            row = self.get_task(task_id)
            if row:
                tasks.append(row)
        return tasks

    def upsert_approval(self, record: ApprovalRecord) -> None:
        """插入/更新审批记录。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO approval_record(incident_id, status, approver, comment, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (incident_id) DO UPDATE SET
                        status=EXCLUDED.status,
                        approver=EXCLUDED.approver,
                        comment=EXCLUDED.comment,
                        updated_at=EXCLUDED.updated_at
                    """,
                    (
                        record.incident_id,
                        record.status.value,
                        record.approver,
                        record.comment,
                        record.created_at,
                        record.updated_at,
                    ),
                )

    def get_approval(self, incident_id: str) -> ApprovalRecord | None:
        """读取审批记录。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT incident_id, status, approver, comment, created_at, updated_at
                    FROM approval_record
                    WHERE incident_id=%s
                    """,
                    (incident_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return ApprovalRecord(
                    incident_id=row[0],
                    status=ApprovalStatus(row[1]),
                    approver=row[2],
                    comment=row[3],
                    created_at=row[4].replace(tzinfo=UTC),
                    updated_at=row[5].replace(tzinfo=UTC),
                )
