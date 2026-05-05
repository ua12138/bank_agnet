"""项目运行配置。

该模块集中管理环境变量与默认值，避免在业务代码中散落硬编码。
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置对象。

    说明：
    - 字段会按 `HZ_AIOPS_` 前缀从 `.env` / 系统环境变量加载。
    - 该对象通过 `get_settings()` 缓存为单例，避免重复解析。
    """

    # 应用基础信息
    app_name: str = "hz-bank-aiops-incident"
    env: Literal["dev", "test", "prod"] = "dev"

    # 工作流引擎开关：classic = 纯 Python 流程，langgraph = 图编排流程
    workflow_engine: Literal["classic", "langgraph"] = "langgraph"
    # 当 langgraph 依赖缺失时，是否自动降级到 classic
    langgraph_fallback_to_classic: bool = True
    # ReAct 的结构化 CoT 轨迹开关与截断策略
    react_cot_enabled: bool = False
    react_cot_max_chars: int = 240
    react_cot_max_entries: int = 16
    react_memory_enabled: bool = True
    react_context_window_steps: int = 3
    react_summary_max_chars: int = 480
    react_summary_max_entries: int = 12

    # 去重与人工审批开关
    enable_dedup: bool = True
    dedup_window_sec: int = 300
    enable_human_approval: bool = True

    # 任务存储配置：本地调试默认 sqlite，生产建议 postgres
    task_db_kind: Literal["sqlite", "postgres"] = "sqlite"
    sqlite_path: str = "./data/runtime/diagnosis.db"
    postgres_dsn: str = ""

    # Worker 运行参数
    worker_id: str = "diag-worker-1"
    max_retry: int = 3
    worker_poll_interval_sec: float = 1.0

    # 外部依赖地址
    feishu_webhook_url: str = ""
    rag_mcp_base_url: str = "http://127.0.0.1:8091"

    # 网络请求超时
    mcp_request_timeout_sec: float = 8.0
    webhook_timeout_sec: float = 5.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HZ_AIOPS_",
        extra="ignore",
    )

    @property
    def sqlite_path_obj(self) -> Path:
        """返回 sqlite 文件的绝对路径。"""
        return Path(self.sqlite_path).resolve()

    @property
    def runtime_ready(self) -> bool:
        """检查当前配置是否具备最小可运行条件。"""
        if self.task_db_kind == "postgres":
            return bool(self.postgres_dsn)
        return True

    # 预留多通知通道（当前主用飞书）
    notify_channels: list[str] = Field(default_factory=lambda: ["feishu"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回缓存后的配置单例。"""
    return Settings()
