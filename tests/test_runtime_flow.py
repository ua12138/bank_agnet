from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from hz_bank_aiops.config import Settings
from hz_bank_aiops.models import ApprovalStatus, IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import DiagnosisRuntime


class RuntimeFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(".pytest_tmp") / f"runtime_flow_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        sqlite_path = str((self.tmp_dir / "runtime.db").resolve())
        self.settings = Settings(
            task_db_kind="sqlite",
            sqlite_path=sqlite_path,
            workflow_engine="classic",
            enable_human_approval=False,
            enable_dedup=True,
            feishu_webhook_url="",
        )
        self.runtime = DiagnosisRuntime(self.settings)
        self.runtime.init_schema()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_submit_and_process_one(self) -> None:
        incident = IncidentPayload(
            incident_id="inc_runtime_1",
            system="payment-system",
            service="payment-api",
            severity=Severity.high,
            event_count=6,
            window_start="2025-08-01T10:10:00Z",
            window_end="2025-08-01T10:15:00Z",
            hosts=["db-prod-01", "api-prod-01"],
            metrics=[IncidentMetric(metric="mysql.connections", value=980)],
            recent_change_ids=["chg_1001"],
        )
        task_id = self.runtime.submit_incident(incident)
        self.assertGreater(task_id, 0)

        out = self.runtime.process_one_task(worker_id="test-worker")
        self.assertTrue(out["claimed"])
        self.assertEqual(out["status"], "DONE")

    def test_approval_submit(self) -> None:
        row = self.runtime.submit_approval(
            incident_id="inc_ap_1",
            status=ApprovalStatus.approved,
            approver="alice",
            comment="ok",
        )
        self.assertEqual(row.status, ApprovalStatus.approved)
        found = self.runtime.get_approval("inc_ap_1")
        self.assertIsNotNone(found)
        self.assertEqual(found.status, ApprovalStatus.approved)


if __name__ == "__main__":
    unittest.main()
