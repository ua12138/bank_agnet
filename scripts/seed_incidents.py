from __future__ import annotations

"""调试脚本：批量注入样例 incident 到任务队列。"""

import json
from pathlib import Path

from hz_bank_aiops.config import get_settings
from hz_bank_aiops.models import IncidentPayload
from hz_bank_aiops.service import DiagnosisRuntime


def main() -> None:
    # 读取 data/sample/incidents.json 并逐条入队
    settings = get_settings()
    runtime = DiagnosisRuntime(settings)
    runtime.init_schema()

    path = Path("data/sample/incidents.json")
    items = json.loads(path.read_text(encoding="utf-8"))
    for obj in items:
        incident = IncidentPayload.model_validate(obj)
        task_id = runtime.submit_incident(incident)
        print(f"enqueued incident={incident.incident_id} task_id={task_id}")


if __name__ == "__main__":
    main()
