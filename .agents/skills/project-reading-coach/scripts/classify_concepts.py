from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from bootstrap import ensure_shared_on_path
ROOT = ensure_shared_on_path(__file__)

from io_utils import read_json, write_json


MUST_FIRST = {
    "fastapi_router", "fastapi_app", "pydantic_model", "pydantic_validation",
    "dependency_injection", "workflow_execute", "workflow_invoke",
    "langgraph_stategraph", "task_claiming", "retriever", "reranker",
    "mcp_server", "mcp_dispatch", "source", "transform", "aggregate", "sink",
}

LEARN_WHILE_READING = {
    "route_decorator", "async_handler", "langgraph_node", "langgraph_edge",
    "langgraph_conditional_edge", "react_tool_trace", "approval_flow",
    "retry_and_failure", "notify_flow", "vectorstore", "embedding",
    "context_builder", "generator", "mcp_tool", "mcp_resource", "mcp_prompt",
    "window", "streaming", "status_machine", "run_once", "run_forever",
}

CAN_IGNORE_TEMP = set()


def classify(concepts_by_file: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
    result: Dict[str, Dict[str, List[str]]] = defaultdict(dict)

    for file, concepts in concepts_by_file.items():
        for concept in concepts:
            if concept in MUST_FIRST:
                bucket = "must_understand_first"
            elif concept in LEARN_WHILE_READING:
                bucket = "learn_while_reading"
            else:
                bucket = "can_ignore_temporarily"

            result[bucket].setdefault(file, [])
            if concept not in result[bucket][file]:
                result[bucket][file].append(concept)

    return dict(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="对知识点做初步分层")
    parser.add_argument("--in", dest="input_file", required=True, help="输入 JSON")
    parser.add_argument("--out", required=True, help="输出 JSON")
    args = parser.parse_args()

    input_path = Path(args.input_file).resolve()
    out_path = Path(args.out).resolve()

    raw = read_json(input_path)
    result = classify(raw)
    write_json(out_path, result)
    print(f"[OK] concepts_classified -> {out_path}")


if __name__ == "__main__":
    main()
