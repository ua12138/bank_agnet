# Executive Summary

## 1. Project Type
- FastAPI backend
- Agent application
- LangGraph application
- MCP client application
- Data processing pipeline

## 2. What This Project Does
这个项目把上游 Flink 聚合后的 `incident` 写入任务表，再由 Worker 读取任务，经过“去重 -> 审批 -> ReAct 诊断 -> 结果落库 -> 通知”完成一次 AIOps 诊断流程。  
Code: `src/hz_bank_aiops/api/main.py::submit_incident`  
Code: `src/hz_bank_aiops/service/runtime.py::process_one_task`  
Code: `src/hz_bank_aiops/service/workflow.py::execute`

## 3. What the Beginner Should Understand First
1. 这是一个“API 收任务，Worker 做处理”的项目，不是单纯的聊天接口。  
2. `DiagnosisRuntime` 是全项目最重要的“总装配器”。  
3. `IncidentDiagnosisWorkflow` 负责治理流程，`ReActAgent` 负责诊断推理。  
4. 这个仓库里没有完整的本地 RAG 检索链，而是通过 MCP 客户端去调用外部 RAG 服务。  
Code: `src/hz_bank_aiops/service/runtime.py::DiagnosisRuntime`  
Code: `src/hz_bank_aiops/agent/react_agent.py::ReActAgent`  
Code: `src/hz_bank_aiops/mcp/rag_client.py::RagMCPClient`

## 4. Main Runtime Flow
```text
POST /api/v1/incidents
  -> api.main.submit_incident
  -> runtime.submit_incident
  -> task_store.enqueue_incident

Worker loop / run-once
  -> runtime.process_one_task
  -> task_store.claim_next_task
  -> workflow.execute
     -> control_center.check_duplicate
     -> control_center.ensure_approval
     -> react_agent / langgraph_react
  -> task_store.save_result
  -> notifier.send
  -> task_store.mark_done / mark_failed
```

## 5. Most Important Files
- `src/hz_bank_aiops/api/main.py`：FastAPI 入口
- `src/hz_bank_aiops/service/runtime.py`：运行时总入口
- `src/hz_bank_aiops/service/workflow.py`：治理和编排
- `src/hz_bank_aiops/agent/react_agent.py`：经典 ReAct
- `src/hz_bank_aiops/agent/langgraph_react.py`：LangGraph 版 ReAct
- `src/hz_bank_aiops/storage/task_store.py`：任务/结果/审批持久化
- `src/hz_bank_aiops/service/control_center.py`：去重与审批
- `src/hz_bank_aiops/tools/ops_tools.py`：诊断工具集合
- `src/hz_bank_aiops/mcp/rag_client.py`：外部 RAG MCP 客户端

## 6. Learning Difficulty Assessment
Level 4 - Agent / LangGraph / MCP service

原因：
- 不只是 FastAPI，而是“API + Worker + 存储 + Agent + 外部服务”的组合项目。
- 存在两条推理路径：`classic` 与 `langgraph`。
- 你需要同时理解任务状态、治理流程、工具调用、MCP 外部依赖。
- 但它仍然保留了比较清晰的模块边界，没有复杂的分布式调度器，所以还不到 Level 5。

## 7. Recommended Reading Order
1. `docs/learning/01_PROJECT_MAP.md`
2. `docs/learning/02_STARTUP_FLOW.md`
3. `docs/learning/03_REQUEST_FLOW.md`
4. `src/hz_bank_aiops/api/main.py`
5. `src/hz_bank_aiops/service/runtime.py`
6. `src/hz_bank_aiops/service/workflow.py`
7. `src/hz_bank_aiops/agent/react_agent.py`
8. `src/hz_bank_aiops/storage/task_store.py`
9. `src/hz_bank_aiops/service/control_center.py`
10. `demotest/app/main.py`

## 8. What Not to Read First
- 不要一开始先读 `tests/` 全量文件。
- 不要一开始先读 `flinksql/` 细节 SQL。
- 不要先研究所有注释和所有枚举，先抓主链路。
- 不要把 `LangGraph` 和 `MCP` 想得太大，先把它们当成“流程图引擎”和“外部工具协议”。
