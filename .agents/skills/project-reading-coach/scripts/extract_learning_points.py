from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap import ensure_shared_on_path
ROOT = ensure_shared_on_path(__file__)

from concept_utils import extract_concepts_from_project
from io_utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="提取项目中的框架/主链路知识点")
    parser.add_argument("--project-root", default=str(ROOT), help="项目根目录")
    parser.add_argument("--out", required=True, help="输出 JSON 文件")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    out_path = Path(args.out).resolve()

    data = extract_concepts_from_project(project_root)
    write_json(out_path, data)
    print(f"[OK] concepts_raw -> {out_path}")


if __name__ == "__main__":
    main()
