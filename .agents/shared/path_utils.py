from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.symbols: List[Dict[str, Any]] = []
        self._class_stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.symbols.append({
            "name": node.name,
            "type": "class",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "parent": ".".join(self._class_stack) if self._class_stack else None,
        })
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.symbols.append({
            "name": node.name,
            "type": "method" if self._class_stack else "function",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "parent": ".".join(self._class_stack) if self._class_stack else None,
            "decorators": [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else [],
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.symbols.append({
            "name": node.name,
            "type": "async_method" if self._class_stack else "async_function",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "parent": ".".join(self._class_stack) if self._class_stack else None,
            "decorators": [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else [],
        })
        self.generic_visit(node)


class CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: List[str] = []

    def visit_Call(self, node: ast.Call) -> Any:
        try:
            name = ast.unparse(node.func)
            self.calls.append(name)
        except Exception:
            pass
        self.generic_visit(node)


def extract_symbols_from_file(py_file: Path) -> List[Dict[str, Any]]:
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    visitor = SymbolVisitor()
    visitor.visit(tree)
    return visitor.symbols


def collect_all_symbols(root: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for py_file in root.rglob("*.py"):
        if ".venv" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        try:
            symbols = extract_symbols_from_file(py_file)
        except Exception as exc:
            items.append({
                "file": str(py_file.relative_to(root)),
                "error": str(exc),
            })
            continue

        items.append({
            "file": str(py_file.relative_to(root)),
            "symbols": symbols,
        })
    return items


def get_file_snippet(path: Path, start_line: int, end_line: int, pad: int = 2) -> str:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    lo = max(1, start_line - pad)
    hi = min(len(lines), end_line + pad)
    return "\n".join(lines[lo - 1:hi]).strip()


def collect_calls_in_range(path: Path, start_line: int, end_line: int) -> List[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    snippet = "\n".join(lines[start_line - 1:end_line])
    try:
        tree = ast.parse(snippet)
    except SyntaxError:
        return []
    collector = CallCollector()
    collector.visit(tree)
    return collector.calls


def find_symbol_by_name(symbols: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    target = name.split(".")[-1]
    for item in symbols:
        file_path = item.get("file", "")
        for sym in item.get("symbols", []):
            if sym.get("name") == target:
                found = dict(sym)
                found["file"] = file_path
                return found
    return None
