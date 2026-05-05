"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""Tool 抽象基类。

ReAct 的 act 阶段通过统一接口调用外部能力，便于替换真实实现/Mock 实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Tool：封装该领域职责，供上层流程统一调用。"""

    name: str
    description: str

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """run：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        raise NotImplementedError
