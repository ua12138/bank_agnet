"""存储工厂：根据配置选择 SQLite 或 PostgreSQL 实现。"""

from pathlib import Path

from hz_bank_aiops.config import Settings
from hz_bank_aiops.storage.task_store import PostgresTaskStore, SQLiteTaskStore, TaskStore


def build_task_store(settings: Settings) -> TaskStore:
    """按配置实例化任务存储。

    设计目标：
    - 本地开发零依赖（sqlite）
    - 生产可切换为 postgres 并发消费
    """
    if settings.task_db_kind == "postgres":
        if not settings.postgres_dsn:
            raise RuntimeError("HZ_AIOPS_POSTGRES_DSN is required when task_db_kind=postgres")
        return PostgresTaskStore(dsn=settings.postgres_dsn, max_retry_default=settings.max_retry)
    return SQLiteTaskStore(
        db_path=Path(settings.sqlite_path).resolve(),
        max_retry_default=settings.max_retry,
    )
