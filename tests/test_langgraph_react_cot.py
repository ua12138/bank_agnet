from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from hz_bank_aiops.config import Settings
from hz_bank_aiops.models import IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import DiagnosisRuntime


class LangGraphReActCoTTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(".pytest_tmp") / f"langgraph_cot_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _build_runtime(self, cot_enabled: bool) -> DiagnosisRuntime:
        settings = Settings(
            task_db_kind="sqlite",
            sqlite_path=str((self.tmp_dir / f"runtime_{uuid.uuid4().hex}.db").resolve()),
            workflow_engine="langgraph",
            langgraph_fallback_to_classic=True,
            enable_dedup=False,
            enable_human_approval=False,
            feishu_webhook_url="",
            react_cot_enabled=cot_enabled,
            react_cot_max_chars=80,
            react_cot_max_entries=4,
        )
        runtime = DiagnosisRuntime(settings)
        runtime.init_schema()
        return runtime

    def _incident(self, incident_id: str) -> IncidentPayload:
        return IncidentPayload(
            incident_id=incident_id,
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

    def test_langgraph_writes_cot_trace_when_enabled(self) -> None:
        runtime = self._build_runtime(cot_enabled=True)
        if runtime.resolved_workflow_engine != "langgraph":
            self.skipTest("langgraph is not installed in current test environment")

        runtime.submit_incident(self._incident("inc_langgraph_cot_on"))
        out = runtime.process_one_task(worker_id="test-worker")
        self.assertEqual(out["status"], "DONE")
        cot = out["result"]["result_json"].get("cot")
        self.assertIsNotNone(cot)
        self.assertTrue(cot["enabled"])
        self.assertGreaterEqual(len(cot["trace"]), 2)
        self.assertLessEqual(len(cot["trace"]), 4)
        for line in cot["trace"]:
            self.assertLessEqual(len(line), 80)

    def test_langgraph_does_not_write_cot_trace_when_disabled(self) -> None:
        runtime = self._build_runtime(cot_enabled=False)
        if runtime.resolved_workflow_engine != "langgraph":
            self.skipTest("langgraph is not installed in current test environment")

        runtime.submit_incident(self._incident("inc_langgraph_cot_off"))
        out = runtime.process_one_task(worker_id="test-worker")
        self.assertEqual(out["status"], "DONE")
        self.assertNotIn("cot", out["result"]["result_json"])


if __name__ == "__main__":
    unittest.main()

