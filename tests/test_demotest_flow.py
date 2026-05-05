"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from demotest.app.db import DemoSQLite
from demotest.app.react_tools import PseudoReActEngine
from demotest.app.worker import DemoWorker


class DemoTestFlowCase(unittest.TestCase):
    """DemoTestFlowCase：封装该领域职责，供上层流程统一调用。"""
    def test_demotest_worker_once(self) -> None:
        """test_demotest_worker_once：测试意图是验证该场景下的行为与预期结果一致。"""
        tmp_dir = Path(".pytest_tmp") / f"demotest_{uuid.uuid4().hex}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            db = DemoSQLite(tmp_dir / "demo.db")
            db.init()
            db.insert_task(
                {
                    "incident_id": "demo_inc_test",
                    "system": "payment-system",
                    "service": "payment-api",
                    "severity": "high",
                    "hosts": ["db-prod-01"],
                    "metrics": [{"metric": "mysql.connections", "value": 980}],
                    "recent_change_ids": ["chg_1001"],
                }
            )
            worker = DemoWorker(
                db=db,
                engine=PseudoReActEngine(rag_mcp_base_url="http://127.0.0.1:65530"),
            )
            out = worker.run_once()
            self.assertTrue(out["claimed"])
            self.assertGreater(len(out["reasoning"]), 0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
