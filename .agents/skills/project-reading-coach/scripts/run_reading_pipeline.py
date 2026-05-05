from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def script_supports_arg(script_path: Path, arg_name: str) -> bool:
    """
    通过 `--help` 粗略判断脚本是否支持某个参数。
    这样可以兼容不同版本的 make_reading_guide.py / make_project_demo.py。
    """
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        help_text = (result.stdout or "") + "\n" + (result.stderr or "")
        return arg_name in help_text
    except Exception:
        return False


def find_existing_script(script_dir: Path, candidates: list[str]) -> Path:
    for name in candidates:
        p = script_dir / name
        if p.exists():
            return p
    raise FileNotFoundError(
        f"在 {script_dir} 下找不到候选脚本：{', '.join(candidates)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="兼容型 project-reading-coach pipeline")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument(
        "--artifacts-dir",
        default=".artifacts/project-reading-coach",
        help="中间工件目录",
    )
    parser.add_argument(
        "--guide-out",
        default="PROJECT_READING_GUIDE.md",
        help="导读文档输出路径",
    )
    parser.add_argument(
        "--demo-out",
        default="project_demo.py",
        help="demo 输出路径",
    )
    parser.add_argument(
        "--mode",
        default="worker_task",
        help="demo 模式；当 demo 脚本需要 --mode 时使用",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    guide_out = Path(args.guide_out).resolve()
    demo_out = Path(args.demo_out).resolve()

    script_dir = Path(__file__).resolve().parent

    extract_script = script_dir / "extract_learning_points.py"
    classify_script = script_dir / "classify_concepts.py"

    guide_script = find_existing_script(
        script_dir,
        [
            "make_reading_guide.py",
            "make_reading_guide_strict.py",
            "make_reading_guide.pattern_driven.py",
        ],
    )

    demo_script = find_existing_script(
        script_dir,
        [
            "make_project_demo.py",
            "make_project_demo_strict.py",
            "make_framework_demo.py",
        ],
    )

    raw_concepts = artifacts_dir / "concepts_raw.json"
    classified_concepts = artifacts_dir / "concepts_classified.json"

    # 1) 尽量生成中间工件，但不让它们阻塞最终主产物
    if extract_script.exists():
        run([
            sys.executable,
            str(extract_script),
            "--project-root",
            str(project_root),
            "--out",
            str(raw_concepts),
        ])
    else:
        print("[SKIP] 未找到 extract_learning_points.py，跳过 concepts_raw.json 生成")

    if classify_script.exists() and raw_concepts.exists():
        run([
            sys.executable,
            str(classify_script),
            "--in",
            str(raw_concepts),
            "--out",
            str(classified_concepts),
        ])
    else:
        print("[SKIP] 未找到 classify_concepts.py 或 concepts_raw.json，跳过 concepts_classified.json 生成")

    # 2) 生成 guide：按当前脚本真实参数签名调用
    guide_cmd = [sys.executable, str(guide_script)]

    if script_supports_arg(guide_script, "--project-root"):
        guide_cmd.extend(["--project-root", str(project_root)])

    if script_supports_arg(guide_script, "--concepts") and classified_concepts.exists():
        guide_cmd.extend(["--concepts", str(classified_concepts)])

    if script_supports_arg(guide_script, "--out"):
        guide_cmd.extend(["--out", str(guide_out)])
    else:
        raise RuntimeError(f"{guide_script.name} 不支持 --out，无法生成导读文档")

    run(guide_cmd)

    # 3) 生成 demo：同样按脚本真实参数签名调用
    demo_cmd = [sys.executable, str(demo_script)]

    if script_supports_arg(demo_script, "--mode"):
        demo_cmd.extend(["--mode", args.mode])

    if script_supports_arg(demo_script, "--project-root"):
        demo_cmd.extend(["--project-root", str(project_root)])

    if script_supports_arg(demo_script, "--out"):
        demo_cmd.extend(["--out", str(demo_out)])
    else:
        raise RuntimeError(f"{demo_script.name} 不支持 --out，无法生成 demo")

    run(demo_cmd)

    print()
    print("[DONE] 已生成：")
    print(f"  - {guide_out}")
    print(f"  - {demo_out}")

    if raw_concepts.exists():
        print("[INFO] 中间工件：")
        print(f"  - {raw_concepts}")
    if classified_concepts.exists():
        print(f"  - {classified_concepts}")


if __name__ == "__main__":
    main()
