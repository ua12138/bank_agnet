"""模块说明：该文件用于承载项目中的相关实现。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    """DemoSettings：封装该领域职责，供上层流程统一调用。"""

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
        """sqlite_path_obj：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return Path(self.sqlite_path).resolve()


def get_demo_settings() -> DemoSettings:
    """get_demo_settings：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    return DemoSettings()
