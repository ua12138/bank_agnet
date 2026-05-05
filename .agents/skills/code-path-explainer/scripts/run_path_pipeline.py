from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from bootstrap import ensure_shared_on_path
ROOT = ensure_shared_on_path(__file__)


def run(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="一键生成项目模式驱动的代码链路报告")
    parser.add_argument("--project-root", default=str(ROOT), help="项目根目录")
    parser.add_argument("--feature", required=True, help="功能关键词")
    parser.add_argument(
        "--artifacts-dir",
        default=str(Path(ROOT) / ".artifacts" / "code-path-explainer"),
        help="中间工件目录",
    )
    parser.add_argument(
        "--report-out",
        default=str(Path(ROOT) / "CODE_PATH_REPORT.md"),
        help="最终报告输出路径",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    report_out = Path(args.report_out).resolve()

    symbols_out = artifacts_dir / "symbols.json"

    py = sys.executable
    script_dir = Path(__file__).resolve().parent

    run([
        py, str(script_dir / "extract_symbols.py"),
        "--project-root", str(project_root),
        "--out", str(symbols_out),
    ])

    run([
        py, str(script_dir / "make_path_report.py"),
        "--project-root", str(project_root),
        "--symbols", str(symbols_out),
        "--feature", args.feature,
        "--out", str(report_out),
    ])

    print()
    print("[DONE] 已生成：")
    print(f"  - {report_out}")
    print("[INFO] 中间工件：")
    print(f"  - {symbols_out}")


if __name__ == "__main__":
    main()
