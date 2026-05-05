"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""核心数据模型定义。

该文件统一描述：
- 告警/事件输入
- 任务状态
- 诊断结果
- 审批与通知对象
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity：封装该领域职责，供上层流程统一调用。"""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, Enum):
    """TaskStatus：封装该领域职责，供上层流程统一调用。"""

    new = "NEW"
    processing = "PROCESSING"
    done = "DONE"
    failed = "FAILED"
    observing = "OBSERVING"
    resolved = "RESOLVED"


class NotifyStatus(str, Enum):
    """NotifyStatus：封装该领域职责，供上层流程统一调用。"""

    pending = "PENDING"
    sent = "SENT"
    failed = "FAILED"
    skipped = "SKIPPED"


class ApprovalStatus(str, Enum):
    """ApprovalStatus：封装该领域职责，供上层流程统一调用。"""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_approved = "auto_approved"


class AlertEvent(BaseModel):
    """AlertEvent：封装该领域职责，供上层流程统一调用。"""

    event_id: str
    source: str = "zabbix"
    host: str
    service: str
    system: str
    metric: str
    value: float
    severity: Severity
    timestamp: datetime
    message: str


class IncidentMetric(BaseModel):
    """IncidentMetric：封装该领域职责，供上层流程统一调用。"""

    metric: str
    value: float


class IncidentPayload(BaseModel):
    """IncidentPayload：封装该领域职责，供上层流程统一调用。"""

    incident_id: str
    system: str
    service: str
    severity: Severity
    event_count: int
    window_start: datetime
    window_end: datetime
    hosts: list[str]
    metrics: list[IncidentMetric]
    recent_change_ids: list[str] = Field(default_factory=list)
    status: str = "NEW"


class DiagnosisTask(BaseModel):
    """DiagnosisTask：封装该领域职责，供上层流程统一调用。"""

    id: int | None = None
    incident_id: str
    system_name: str
    service_name: str = ""
    priority: str = "P2"
    status: TaskStatus = TaskStatus.new
    payload_json: dict[str, Any]
    retry_count: int = 0
    max_retry: int = 3
    worker_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str = ""
    need_notify: bool = True
    notify_status: NotifyStatus = NotifyStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RootCauseCandidate(BaseModel):
    """RootCauseCandidate：封装该领域职责，供上层流程统一调用。"""

    cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ToolTraceStep(BaseModel):
    """ToolTraceStep：封装该领域职责，供上层流程统一调用。"""

    index: int
    thought: str
    action: str
    action_input: dict[str, Any] = Field(default_factory=dict)
    observation: dict[str, Any] = Field(default_factory=dict)


class DiagnosisResult(BaseModel):
    """DiagnosisResult：封装该领域职责，供上层流程统一调用。"""

    incident_id: str
    root_cause_top1: str
    root_cause_candidates: list[RootCauseCandidate] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    llm_model: str = "mock-ops-llm"
    tool_trace: list[ToolTraceStep] = Field(default_factory=list)
    result_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRecord(BaseModel):
    """ApprovalRecord：封装该领域职责，供上层流程统一调用。"""

    incident_id: str
    status: ApprovalStatus
    approver: str = ""
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalDecisionRequest(BaseModel):
    """ApprovalDecisionRequest：封装该领域职责，供上层流程统一调用。"""

    status: ApprovalStatus
    approver: str
    comment: str = ""


class FeishuMessage(BaseModel):
    """FeishuMessage：封装该领域职责，供上层流程统一调用。"""

    incident_id: str
    title: str
    content: str


class TaskClaimResult(BaseModel):
    """TaskClaimResult：封装该领域职责，供上层流程统一调用。"""

    claimed: bool
    task: DiagnosisTask | None = None
