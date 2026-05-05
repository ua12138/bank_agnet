"""模块说明：该文件用于承载项目中的相关实现。"""

from pathlib import Path

from hz_bank_aiops.config import Settings
from hz_bank_aiops.storage.task_store import PostgresTaskStore, SQLiteTaskStore, TaskStore


def build_task_store(settings: Settings) -> TaskStore:
    """build_task_store：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    if settings.task_db_kind == "postgres":
        if not settings.postgres_dsn:
            raise RuntimeError("HZ_AIOPS_POSTGRES_DSN is required when task_db_kind=postgres")
        return PostgresTaskStore(dsn=settings.postgres_dsn, max_retry_default=settings.max_retry)
    return SQLiteTaskStore(
        db_path=Path(settings.sqlite_path).resolve(),
        max_retry_default=settings.max_retry,
    )
