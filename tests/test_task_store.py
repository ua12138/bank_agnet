"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from hz_bank_aiops.models import DiagnosisResult, NotifyStatus, RootCauseCandidate
from hz_bank_aiops.storage.task_store import SQLiteTaskStore, TaskStatus


class SQLiteTaskStoreTestCase(unittest.TestCase):
    """SQLiteTaskStoreTestCase：封装该领域职责，供上层流程统一调用。"""
    def setUp(self) -> None:
        """测试准备：创建测试环境、样例数据与依赖对象。"""
        self.tmp_dir = Path(".pytest_tmp") / f"task_store_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.tmp_dir / "task.db"
        self.store = SQLiteTaskStore(db_path=db_path, max_retry_default=3)
        self.store.init_schema()

    def tearDown(self) -> None:
        """测试清理：回收临时资源，避免影响后续用例。"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_enqueue_and_claim(self) -> None:
        """test_enqueue_and_claim：测试意图是验证该场景下的行为与预期结果一致。"""
        payload = {
            "incident_id": "inc_test_1",
            "system": "payment-system",
            "service": "payment-api",
            "severity": "high",
            "event_count": 5,
            "window_start": "2025-08-01T10:10:00+00:00",
            "window_end": "2025-08-01T10:15:00+00:00",
            "hosts": ["db-prod-01"],
            "metrics": [{"metric": "mysql.connections", "value": 980}],
            "recent_change_ids": ["chg_1001"],
            "status": "NEW",
        }
        task_id = self.store.enqueue_incident(payload)
        self.assertGreater(task_id, 0)

        claim = self.store.claim_next_task("worker-test")
        self.assertTrue(claim.claimed)
        self.assertIsNotNone(claim.task)
        self.assertEqual(claim.task.id, task_id)
        self.assertEqual(claim.task.status, TaskStatus.processing)

    def test_mark_done_and_save_result(self) -> None:
        """test_mark_done_and_save_result：测试意图是验证该场景下的行为与预期结果一致。"""
        payload = {
            "incident_id": "inc_test_2",
            "system": "payment-system",
            "service": "payment-api",
            "severity": "high",
            "event_count": 5,
            "window_start": "2025-08-01T10:10:00+00:00",
            "window_end": "2025-08-01T10:15:00+00:00",
            "hosts": ["db-prod-01"],
            "metrics": [{"metric": "mysql.connections", "value": 980}],
            "recent_change_ids": [],
            "status": "NEW",
        }
        task_id = self.store.enqueue_incident(payload)
        _ = self.store.claim_next_task("worker-test")
        result = DiagnosisResult(
            incident_id="inc_test_2",
            root_cause_top1="db pool exhausted",
            root_cause_candidates=[RootCauseCandidate(cause="db pool exhausted", confidence=0.8)],
            evidence=["e1"],
            suggestions=["s1"],
            confidence=0.8,
            result_json={"ok": True},
        )
        result_id = self.store.save_result(result)
        self.assertGreater(result_id, 0)
        self.store.mark_done(task_id, NotifyStatus.sent)
        task = self.store.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.status, TaskStatus.done)


if __name__ == "__main__":
    unittest.main()
