from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap import ensure_shared_on_path
ROOT = ensure_shared_on_path(__file__)

from io_utils import write_json
from path_utils import collect_all_symbols


def main() -> None:
    parser = argparse.ArgumentParser(description="提取项目中的 Python 符号")
    parser.add_argument("--project-root", default=str(ROOT), help="项目根目录")
    parser.add_argument("--out", required=True, help="输出 JSON 文件")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    out_path = Path(args.out).resolve()

    data = collect_all_symbols(project_root)
    write_json(out_path, data)
    print(f"[OK] symbols -> {out_path}")


if __name__ == "__main__":
    main()
