from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# 模式驱动的概念提取规则。
# 重点提取阻塞主链路理解的“框架/模式”概念，而不是基础 Python 概念。
CONCEPT_RULES = [
    ("APIRouter", "fastapi_router"),
    ("FastAPI(", "fastapi_app"),
    ("BaseModel", "pydantic_model"),
    ("model_validate(", "pydantic_validation"),
    ("Depends(", "dependency_injection"),
    ("async def", "async_handler"),
    ("@router.", "route_decorator"),
    ("@app.", "route_decorator"),

    ("StateGraph", "langgraph_stategraph"),
    ("add_node(", "langgraph_node"),
    ("add_edge(", "langgraph_edge"),
    ("add_conditional_edges(", "langgraph_conditional_edge"),
    ("invoke(", "workflow_invoke"),
    ("execute(", "workflow_execute"),
    ("tool_trace", "react_tool_trace"),
    ("approval", "approval_flow"),

    ("mcp", "mcp_server"),
    ("tool", "mcp_tool"),
    ("resource", "mcp_resource"),
    ("prompt", "mcp_prompt"),
    ("dispatch", "mcp_dispatch"),
    ("client", "mcp_client"),

    ("claim_next_task", "task_claiming"),
    ("mark_failed(", "retry_and_failure"),
    ("notify", "notify_flow"),
    ("status", "status_machine"),
    ("run_once", "run_once"),
    ("run_forever", "run_forever"),

    ("retriever", "retriever"),
    ("embedding", "embedding"),
    ("vector", "vectorstore"),
    ("rerank", "reranker"),
    ("similarity_search", "retrieval"),
    ("context", "context_builder"),
    ("generate", "generator"),

    ("source", "source"),
    ("transform", "transform"),
    ("aggregate", "aggregate"),
    ("sink", "sink"),
    ("window", "window"),
    ("stream", "streaming"),
]


def extract_concepts_from_text(text: str) -> List[str]:
    found = []
    lowered = text.lower()
    for pattern, concept in CONCEPT_RULES:
        if pattern.lower() in lowered:
            found.append(concept)
    return sorted(set(found))


def extract_concepts_from_project(root: Path) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for p in root.rglob("*.py"):
        if ".venv" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        concepts = extract_concepts_from_text(text)
        if concepts:
            result[str(p.relative_to(root))] = concepts

    # 额外扫描常见 SQL / 配置 / 文档文件，帮助识别 ETL / MCP / RAG / task 等模式
    for ext in ("*.sql", "*.md", "*.yaml", "*.yml", "*.toml"):
        for p in root.rglob(ext):
            if ".venv" in p.parts or "__pycache__" in p.parts:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            concepts = extract_concepts_from_text(text)
            if concepts:
                result.setdefault(str(p.relative_to(root)), [])
                for c in concepts:
                    if c not in result[str(p.relative_to(root))]:
                        result[str(p.relative_to(root))].append(c)
    return result
