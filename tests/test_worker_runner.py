from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from hz_bank_aiops.config import Settings
from hz_bank_aiops.models import IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import DiagnosisRuntime
from hz_bank_aiops.worker import WorkerRunner


class WorkerRunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(".pytest_tmp") / f"worker_runner_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        settings = Settings(
            task_db_kind="sqlite",
            sqlite_path=str((self.tmp_dir / "worker.db").resolve()),
            workflow_engine="classic",
            enable_human_approval=False,
            feishu_webhook_url="",
        )
        self.runtime = DiagnosisRuntime(settings)
        self.runtime.init_schema()
        self.runner = WorkerRunner(self.runtime, worker_id="test-worker", poll_interval_sec=0.1)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_run_once(self) -> None:
        incident = IncidentPayload(
            incident_id="inc_worker_1",
            system="payment-system",
            service="payment-api",
            severity=Severity.high,
            event_count=6,
            window_start="2025-08-01T10:10:00Z",
            window_end="2025-08-01T10:15:00Z",
            hosts=["db-prod-01"],
            metrics=[IncidentMetric(metric="mysql.connections", value=980)],
            recent_change_ids=["chg_1001"],
        )
        self.runtime.submit_incident(incident)
        out = self.runner.run_once()
        self.assertTrue(out["claimed"])
        self.assertEqual(out["status"], "DONE")


if __name__ == "__main__":
    unittest.main()
