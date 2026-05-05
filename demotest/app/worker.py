"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""demotest worker：最小化任务消费器。"""

import json

from demotest.app.db import DemoSQLite
from demotest.app.react_tools import PseudoReActEngine


class DemoWorker:
    """DemoWorker：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, db: DemoSQLite, engine: PseudoReActEngine) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.db = db
        self.engine = engine

    def run_once(self) -> dict:
        """run_once：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        task = self.db.claim_task()
        if not task:
            return {"claimed": False, "message": "no task"}

        payload = json.loads(task["payload_json"])
        # 调用伪 ReAct 引擎生成 reasoning 与 summary
        output = self.engine.run(payload)
        self.db.save_result(
            incident_id=payload["incident_id"],
            summary=output["summary"],
            reasoning=output["reasoning"],
        )
        self.db.mark_done(int(task["id"]))
        return {
            "claimed": True,
            "task_id": int(task["id"]),
            "incident_id": payload["incident_id"],
            "summary": output["summary"],
            "reasoning": output["reasoning"],
        }
