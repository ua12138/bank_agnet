from __future__ import annotations

from pathlib import Path
from typing import Dict, List


README_NAMES = {"README.md", "readme.md", "README.MD"}
ENTRYPOINT_CANDIDATES = {
    "main.py",
    "app.py",
    "server.py",
    "cli.py",
    "__main__.py",
    "manage.py",
}
SPEC_KEYWORDS = ("spec", "requirements", "design", "architecture")
ACCEPTANCE_KEYWORDS = ("acceptance", "uat", "testcase", "test_case")


def _find_files_by_keywords(root: Path, keywords: tuple[str, ...]) -> List[str]:
    matched: List[str] = []
    for p in root.rglob("*"):
        if p.is_file() and any(k in p.name.lower() for k in keywords):
            matched.append(str(p.relative_to(root)))
    return sorted(matched)


def _find_readmes(root: Path) -> List[str]:
    matched: List[str] = []
    for p in root.rglob("*"):
        if p.is_file() and p.name in README_NAMES:
            matched.append(str(p.relative_to(root)))
    return sorted(matched)


def _find_entrypoints(root: Path) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for p in root.rglob("*"):
        if p.is_file() and p.name in ENTRYPOINT_CANDIDATES:
            items.append({
                "file": str(p.relative_to(root)),
                "reason": "common_entrypoint_filename",
            })

    for dirname in [
        "api", "routes", "router", "service", "services", "workflow", "graph",
        "agent", "storage", "repository", "worker", "notifier", "config",
        "mcp", "retriever", "vectorstore", "pipeline", "flinksql"
    ]:
        for p in root.rglob(dirname):
            if p.is_dir():
                items.append({
                    "file": str(p.relative_to(root)),
                    "reason": f"important_directory:{dirname}",
                })

    return items


def build_project_index(root: Path) -> Dict:
    top_level_dirs = sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )

    return {
        "root": str(root),
        "readmes": _find_readmes(root),
        "spec_files": _find_files_by_keywords(root, SPEC_KEYWORDS),
        "acceptance_files": _find_files_by_keywords(root, ACCEPTANCE_KEYWORDS),
        "entrypoints": _find_entrypoints(root),
        "top_level_dirs": top_level_dirs,
    }
