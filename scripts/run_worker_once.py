"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""调试脚本：执行一次 worker 消费。"""

import json

from hz_bank_aiops.config import get_settings
from hz_bank_aiops.service import DiagnosisRuntime
from hz_bank_aiops.worker import WorkerRunner


def main() -> None:
    # 脚本入口：初始化运行时后消费一条任务并打印结构化结果
    """main：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    settings = get_settings()
    runtime = DiagnosisRuntime(settings)
    runtime.init_schema()
    runner = WorkerRunner(runtime=runtime, worker_id=settings.worker_id, poll_interval_sec=0.1)
    out = runner.run_once()
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
