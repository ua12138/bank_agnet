"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

"""Worker 入口。

职责：轮询任务队列并调用 DiagnosisRuntime 处理任务。
"""

import argparse
import json
import time

from hz_bank_aiops.config import get_settings
from hz_bank_aiops.service import DiagnosisRuntime


class WorkerRunner:
    """WorkerRunner：封装该领域职责，供上层流程统一调用。"""

    def __init__(self, runtime: DiagnosisRuntime, worker_id: str, poll_interval_sec: float = 1.0) -> None:
        """初始化对象：注入依赖并保存运行所需配置。"""
        self.runtime = runtime
        self.worker_id = worker_id
        self.poll_interval_sec = poll_interval_sec

    def run_forever(self) -> None:
        """run_forever：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        while True:
            result = self.runtime.process_one_task(worker_id=self.worker_id)
            if result.get("claimed"):
                print(json.dumps(result, ensure_ascii=False))
            else:
                time.sleep(self.poll_interval_sec)

    def run_once(self) -> dict:
        """run_once：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
        return self.runtime.process_one_task(worker_id=self.worker_id)


def run_worker_cli() -> None:
    """run_worker_cli：执行该步骤的核心逻辑，输入输出见参数与返回值定义。"""
    parser = argparse.ArgumentParser(description="Run diagnosis worker.")
    parser.add_argument("--once", action="store_true", help="Process one task and exit")
    args = parser.parse_args()

    settings = get_settings()
    runtime = DiagnosisRuntime(settings)
    runtime.init_schema()
    runner = WorkerRunner(
        runtime=runtime,
        worker_id=settings.worker_id,
        poll_interval_sec=settings.worker_poll_interval_sec,
    )
    if args.once:
        print(json.dumps(runner.run_once(), ensure_ascii=False, indent=2))
        return
    runner.run_forever()
