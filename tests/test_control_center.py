from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from hz_bank_aiops.models import IncidentMetric, IncidentPayload, Severity
from hz_bank_aiops.service import IncidentControlCenter
from hz_bank_aiops.storage.task_store import SQLiteTaskStore


class ControlCenterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(".pytest_tmp") / f"control_center_{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        store = SQLiteTaskStore(self.tmp_dir / "cc.db")
        store.init_schema()
        self.cc = IncidentControlCenter(store=store, dedup_window_sec=300)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _incident(self, incident_id: str) -> IncidentPayload:
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
        first = self.cc.check_duplicate(self._incident("inc_a"))
        second = self.cc.check_duplicate(self._incident("inc_b"))
        self.assertFalse(first["is_duplicate"])
        self.assertTrue(second["is_duplicate"])
        self.assertEqual(second["duplicate_of"], "inc_a")


if __name__ == "__main__":
    unittest.main()
