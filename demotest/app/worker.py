from __future__ import annotations

"""demotest worker：最小化任务消费器。"""

import json

from demotest.app.db import DemoSQLite
from demotest.app.react_tools import PseudoReActEngine


class DemoWorker:
    """串行消费 demo 任务并保存结果。"""

    def __init__(self, db: DemoSQLite, engine: PseudoReActEngine) -> None:
        self.db = db
        self.engine = engine

    def run_once(self) -> dict:
        """单次消费流程。"""
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
