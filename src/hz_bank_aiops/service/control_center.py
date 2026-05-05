"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""控制中心：负责去重判定与人工审批治理。"""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from hz_bank_aiops.models import ApprovalRecord, ApprovalStatus, IncidentPayload, Severity
from hz_bank_aiops.storage import TaskStore


class IncidentControlCenter:
    """IncidentControlCenter：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, store: TaskStore, dedup_window_sec: int = 300) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.store = store
        self.dedup_window_sec = dedup_window_sec
        self._lock = Lock()
        # signature -> [(incident_id, ts), ...]
        self._dedup_index: dict[str, deque[tuple[str, datetime]]] = defaultdict(deque)

    def check_duplicate(self, incident: IncidentPayload) -> dict:
        """check_duplicate：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        signature = self._signature(incident)
        now = self._to_utc(incident.window_end)
        window_start = now - timedelta(seconds=self.dedup_window_sec)

        with self._lock:
            rows = self._dedup_index[signature]
            # 清理窗口外旧记录，控制内存增长
            while rows and rows[0][1] < window_start:
                rows.popleft()
            duplicate_of = ""
            for prev_incident_id, ts in reversed(rows):
                if prev_incident_id != incident.incident_id and ts >= window_start:
                    duplicate_of = prev_incident_id
                    break
            rows.append((incident.incident_id, now))

        return {
            "is_duplicate": bool(duplicate_of),
            "duplicate_of": duplicate_of,
            "signature": signature,
            "window_sec": self.dedup_window_sec,
        }

    def ensure_approval(self, incident: IncidentPayload, enabled: bool) -> ApprovalRecord:
        """ensure_approval：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if not enabled:
            # 人工审批关闭时，统一自动放行
            record = ApprovalRecord(
                incident_id=incident.incident_id,
                status=ApprovalStatus.auto_approved,
                approver="system",
                comment="human approval disabled",
            )
            self.store.upsert_approval(record)
            return record

        existing = self.store.get_approval(incident.incident_id)
        if existing:
            # 幂等：已有审批记录直接返回
            return existing

        if incident.severity in {Severity.low, Severity.medium}:
            # 低/中级告警默认自动审批，避免阻塞处理链路
            record = ApprovalRecord(
                incident_id=incident.incident_id,
                status=ApprovalStatus.auto_approved,
                approver="system",
                comment="non-critical incident auto approved",
            )
            self.store.upsert_approval(record)
            return record

        record = ApprovalRecord(
            incident_id=incident.incident_id,
            status=ApprovalStatus.pending,
            approver="",
            comment="waiting for human approval",
        )
        self.store.upsert_approval(record)
        return record

    def submit_approval(
        self,
        incident_id: str,
        status: ApprovalStatus,
        approver: str,
        comment: str = "",
    ) -> ApprovalRecord:
        """submit_approval：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if status not in {ApprovalStatus.approved, ApprovalStatus.rejected}:
            raise ValueError("manual approval only supports approved/rejected")
        record = ApprovalRecord(
            incident_id=incident_id,
            status=status,
            approver=approver,
            comment=comment,
        )
        self.store.upsert_approval(record)
        return record

    def _signature(self, incident: IncidentPayload) -> str:
        """_signature：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        metric_keys = ",".join(sorted(item.metric for item in incident.metrics))
        hosts = ",".join(sorted(incident.hosts))
        return f"{incident.system}|{incident.service}|{incident.severity.value}|{hosts}|{metric_keys}"

    def _to_utc(self, dt: datetime) -> datetime:
        """_to_utc：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
