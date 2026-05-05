"""demotest 配置。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    """demo 运行参数。"""

    sqlite_path: str = "./demotest/demo_runtime.db"
    rag_mcp_base_url: str = "http://127.0.0.1:8091"
    rag_timeout_sec: float = 60.0
    rag_query_top_k: int = 1
    rag_candidate_multiplier: int = 1
    rag_fast_mode: bool = True
    rag_use_memory: bool = False
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HZ_AIOPS_DEMO_",
        extra="ignore",
    )

    @property
    def sqlite_path_obj(self) -> Path:
        """返回 sqlite 绝对路径。"""
        return Path(self.sqlite_path).resolve()


def get_demo_settings() -> DemoSettings:
    """读取 demo 配置。"""
    return DemoSettings()
