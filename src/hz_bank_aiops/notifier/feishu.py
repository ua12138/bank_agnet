"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""飞书 Webhook 通知组件。"""

import json
from dataclasses import dataclass

import httpx

from hz_bank_aiops.models import DiagnosisResult, FeishuMessage


@dataclass
class FeishuNotifyResult:
    """FeishuNotifyResult：封装该领域职责，供上层流程统一调用。"""

    ok: bool
    message: str = ""
    response_body: dict | None = None


class FeishuNotifier:
    """FeishuNotifier：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, webhook_url: str, timeout_sec: float = 5.0) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.webhook_url = webhook_url
        self.timeout_sec = timeout_sec

    def enabled(self) -> bool:
        """enabled：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return bool(self.webhook_url)

    def build_message(self, result: DiagnosisResult) -> FeishuMessage:
        """build_message：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""

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
        """send：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
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
        """dump_preview：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        message = self.build_message(result)
        return json.dumps(message.model_dump(mode="json"), ensure_ascii=False, indent=2)
