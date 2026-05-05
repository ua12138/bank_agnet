from __future__ import annotations

import sys
from pathlib import Path


def ensure_shared_on_path(current_file: str) -> Path:
    """
    自动把 .agents/shared 加入 sys.path，并返回项目根目录。
    这样脚本可以在 IDE 或命令行中直接运行，不需要手工设置 PYTHONPATH。
    """
    current = Path(current_file).resolve()

    root = None
    for parent in current.parents:
        if (parent / ".agents" / "shared").exists():
            root = parent
            break

    if root is None:
        raise RuntimeError(
            f"无法从脚本路径 {current} 向上定位到项目根目录（未找到 .agents/shared）"
        )

    shared_dir = root / ".agents" / "shared"
    if str(shared_dir) not in sys.path:
        sys.path.insert(0, str(shared_dir))

    return root
