"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from hz_bank_aiops.models import IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import IncidentControlCenter
from hz_bank_aiops.storage.task_store import SQLiteTaskStore


class ControlCenterTestCase(unittest.TestCase):
    """ControlCenterTestCase：封装该领域职责，供上层流程统一调用。"""
    def setUp(self) -> None:
        """测试准备：创建测试环境、样例数据与依赖对象。"""
        self.tmp_dir = Path(".pytest_tmp") / f"control_center_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        store = SQLiteTaskStore(self.tmp_dir / "cc.db")
        store.init_schema()
        self.cc = IncidentControlCenter(store=store, dedup_window_sec=300)

    def tearDown(self) -> None:
        """测试清理：回收临时资源，避免影响后续用例。"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _incident(self, incident_id: str) -> IncidentPayload:
        """_incident：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return IncidentPayload(
            incident_id=incident_id,
            system="payment-system",
            service="payment-api",
            severity=Severity.high,
            event_count=4,
            window_start="2025-08-01T10:10:00Z",
            window_end="2025-08-01T10:15:00Z",
            hosts=["db-prod-01"],
            metrics=[IncidentMetric(metric="mysql.connections", value=980)],
            recent_change_ids=[],
        )

    def test_dedup(self) -> None:
        """test_dedup：测试意图是验证该场景下的行为与预期结果一致。"""
        first = self.cc.check_duplicate(self._incident("inc_a"))
        second = self.cc.check_duplicate(self._incident("inc_b"))
        self.assertFalse(first["is_duplicate"])
        self.assertTrue(second["is_duplicate"])
        self.assertEqual(second["duplicate_of"], "inc_a")


if __name__ == "__main__":
    unittest.main()
