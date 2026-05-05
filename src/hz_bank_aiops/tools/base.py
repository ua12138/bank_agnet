from __future__ import annotations

"""Tool 抽象基类。

ReAct 的 act 阶段通过统一接口调用外部能力，便于替换真实实现/Mock 实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """所有诊断工具的统一协议。"""

    name: str
    description: str

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行工具并返回结构化 observation。"""
        raise NotImplementedError
