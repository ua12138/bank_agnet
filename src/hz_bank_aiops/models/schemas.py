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
    """事件严重级别。"""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, Enum):
    """诊断任务状态机。"""

    new = "NEW"
    processing = "PROCESSING"
    done = "DONE"
    failed = "FAILED"
    observing = "OBSERVING"
    resolved = "RESOLVED"


class NotifyStatus(str, Enum):
    """通知发送状态。"""

    pending = "PENDING"
    sent = "SENT"
    failed = "FAILED"
    skipped = "SKIPPED"


class ApprovalStatus(str, Enum):
    """人工审批状态。"""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_approved = "auto_approved"


class AlertEvent(BaseModel):
    """原始告警事件（偏实时流）。"""

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
    """聚合后 Incident 中的指标快照。"""

    metric: str
    value: float


class IncidentPayload(BaseModel):
    """进入诊断系统的 Incident 载荷。"""

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
    """任务队列表中的诊断任务。"""

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
    """候选根因。"""

    cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ToolTraceStep(BaseModel):
    """单步 Tool 调用轨迹（thought/action/observation）。"""

    index: int
    thought: str
    action: str
    action_input: dict[str, Any] = Field(default_factory=dict)
    observation: dict[str, Any] = Field(default_factory=dict)


class DiagnosisResult(BaseModel):
    """Agent 输出的标准化诊断结果。"""

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
    """审批记录表对象。"""

    incident_id: str
    status: ApprovalStatus
    approver: str = ""
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalDecisionRequest(BaseModel):
    """审批 API 入参。"""

    status: ApprovalStatus
    approver: str
    comment: str = ""


class FeishuMessage(BaseModel):
    """飞书消息体（内部中间对象）。"""

    incident_id: str
    title: str
    content: str


class TaskClaimResult(BaseModel):
    """Worker 抢占任务的结果。"""

    claimed: bool
    task: DiagnosisTask | None = None
