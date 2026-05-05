from __future__ import annotations

"""飞书 Webhook 通知组件。"""

import json
from dataclasses import dataclass

import httpx

from hz_bank_aiops.models import DiagnosisResult, FeishuMessage


@dataclass
class FeishuNotifyResult:
    """飞书发送结果。"""

    ok: bool
    message: str = ""
    response_body: dict | None = None


class FeishuNotifier:
    """诊断结果通知发送器。"""

    def __init__(self, webhook_url: str, timeout_sec: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.timeout_sec = timeout_sec

    def enabled(self) -> bool:
        """仅当配置 webhook 地址时才可发送。"""
        return bool(self.webhook_url)

    def build_message(self, result: DiagnosisResult) -> FeishuMessage:
        """将结构化诊断结果组装为飞书文本。"""

        # 只截取前 3 条证据/建议，避免消息过长影响移动端阅读体验
        evidence = "\n".join(f"- {x}" for x in result.evidence[:3]) or "- None"
        suggestions = "\n".join(f"- {x}" for x in result.suggestions[:3]) or "- None"
        content = (
            f"Incident: {result.incident_id}\n"
            f"Top1 Root Cause: {result.root_cause_top1}\n"
            f"Confidence: {result.confidence:.2f}\n\n"
            f"Evidence:\n{evidence}\n\n"
            f"Suggestions:\n{suggestions}"
        )
        return FeishuMessage(
            incident_id=result.incident_id,
            title=f"[AIOps] Diagnosis {result.incident_id}",
            content=content,
        )

    def send(self, result: DiagnosisResult) -> FeishuNotifyResult:
        """发送飞书通知；失败时返回错误，不抛出到业务主流程。"""
        if not self.enabled():
            return FeishuNotifyResult(ok=False, message="webhook not configured")

        message = self.build_message(result)
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": message.title,
                        "content": [
                            [{"tag": "text", "text": message.content}],
                        ],
                    }
                }
            },
        }
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                resp = client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                # 飞书 webhook 通常以 code=0 表示业务成功
                ok = data.get("code", 0) == 0
                return FeishuNotifyResult(
                    ok=ok,
                    message=data.get("msg", ""),
                    response_body=data,
                )
        except Exception as exc:  # noqa: BLE001
            return FeishuNotifyResult(ok=False, message=str(exc), response_body={"error": str(exc)})

    def dump_preview(self, result: DiagnosisResult) -> str:
        """输出消息预览，便于本地调试。"""
        message = self.build_message(result)
        return json.dumps(message.model_dump(mode="json"), ensure_ascii=False, indent=2)
