"""???????????????????????????"""

from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from hz_bank_aiops.config import Settings
from hz_bank_aiops.models import IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import DiagnosisRuntime


class LangGraphReActMemoryTestCase(unittest.TestCase):
    """LangGraphReActMemoryTestCase???????????????????"""
    def setUp(self) -> None:
        """setUp??????????????????????????"""
        self.tmp_dir = Path(".pytest_tmp") / f"langgraph_memory_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """tearDown??????????????????????????"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _build_runtime(self, memory_enabled: bool) -> DiagnosisRuntime:
        """_build_runtime??????????????????????????"""
        settings = Settings(
            task_db_kind="sqlite",
            sqlite_path=str((self.tmp_dir / f"runtime_{uuid.uuid4().hex}.db").resolve()),
            workflow_engine="langgraph",
            langgraph_fallback_to_classic=True,
            enable_dedup=False,
            enable_human_approval=False,
            feishu_webhook_url="",
            react_cot_enabled=False,
            react_memory_enabled=memory_enabled,
            react_context_window_steps=2,
            react_summary_max_chars=400,
            react_summary_max_entries=8,
        )
        runtime = DiagnosisRuntime(settings)
        runtime.init_schema()
        return runtime

    def _incident(self, incident_id: str) -> IncidentPayload:
        """_incident??????????????????????????"""
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

    def test_memory_summary_is_generated_when_enabled(self) -> None:
        """test_memory_summary_is_generated_when_enabled??????????????????????????"""
        runtime = self._build_runtime(memory_enabled=True)
        if runtime.resolved_workflow_engine != "langgraph":
            self.skipTest("langgraph is not installed in current test environment")

        runtime.submit_incident(self._incident("inc_langgraph_memory_on"))
        out = runtime.process_one_task(worker_id="test-worker")
        self.assertEqual(out["status"], "DONE")

        result_json = out["result"]["result_json"]
        memory = result_json.get("context_memory", {})
        self.assertTrue(memory.get("enabled"))
        self.assertGreaterEqual(memory.get("all_step_count", 0), 4)
        self.assertLessEqual(memory.get("window_step_count", 0), 2)
        self.assertTrue(memory.get("summary"))
        self.assertGreaterEqual(len(memory.get("summary_snapshots", [])), 1)

        # 完整 tool_trace 仍保留，不能被窗口裁剪影响。
        self.assertGreaterEqual(len(out["result"]["tool_trace"]), 4)

    def test_memory_summary_is_empty_when_disabled(self) -> None:
        """test_memory_summary_is_empty_when_disabled??????????????????????????"""
        runtime = self._build_runtime(memory_enabled=False)
        if runtime.resolved_workflow_engine != "langgraph":
            self.skipTest("langgraph is not installed in current test environment")

        runtime.submit_incident(self._incident("inc_langgraph_memory_off"))
        out = runtime.process_one_task(worker_id="test-worker")
        self.assertEqual(out["status"], "DONE")

        result_json = out["result"]["result_json"]
        memory = result_json.get("context_memory", {})
        self.assertFalse(memory.get("enabled"))
        self.assertEqual(memory.get("summary", ""), "")
        self.assertEqual(memory.get("summary_snapshots", []), [])


if __name__ == "__main__":
    unittest.main()
