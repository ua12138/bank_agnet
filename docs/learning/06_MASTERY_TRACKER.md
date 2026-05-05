# Mastery Tracker

| Area | Knowledge Point | Code Location | Current Level | Evidence Required | Next Action |
|---|---|---|---|---|---|
| FastAPI | 路由注册 | `src/hz_bank_aiops/api/main.py` | 1 - can recognize | 能指出 `/api/v1/incidents` 对应函数 | 先跑 `mini_fastapi_skeleton` |
| FastAPI | 请求体到模型 | `api/main.py::submit_incident` | 1 - can recognize | 能解释 `IncidentSubmitRequest` 的作用 | 读 `schemas.py` |
| Runtime | 总装配器 | `service/runtime.py::DiagnosisRuntime` | 0 - unfamiliar | 能画出 runtime 依赖图 | 先读 `02_STARTUP_FLOW.md` |
| Workflow | 去重/审批/ReAct 三段式 | `service/workflow.py` | 0 - unfamiliar | 能说出 classic 和 langgraph 的差异 | 跑 `mini_langgraph_skeleton` |
| Storage | 任务状态机 | `storage/task_store.py` | 1 - can recognize | 能手画 `NEW -> PROCESSING -> DONE/FAILED` | 跑 `mini_storage_skeleton` |
| Agent | ReAct 循环 | `agent/react_agent.py::run` | 0 - unfamiliar | 能解释 `thought/action/observation` | 跑 `mini_agent_skeleton` |
| MCP | 外部 RAG 工具调用 | `mcp/rag_client.py` | 0 - unfamiliar | 能写出 `name + arguments` payload | 跑 `mini_mcp_skeleton` |
| LangGraph | 图状态更新 | `agent/langgraph_react.py` | 0 - unfamiliar | 能说明 `steps` 和 `memory_summary` 的作用 | 对照 `03_REQUEST_FLOW.md` 读 |
| Testing | 从测试反推主流程 | `tests/test_runtime_flow.py` | 1 - can recognize | 能用测试说明主流程怎么跑 | 先读测试再回看实现 |
| Interview | 解释项目架构 | `docs/learning/08_FINAL_PROJECT_REVIEW.md` | 0 - unfamiliar | 能在 3 分钟内完整介绍项目 | 完成 7 天计划后复述 |
