# Knowledge Gap Map

## 1. Python

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| dataclass | `src/hz_bank_aiops/agent/react_agent.py::PlannerContext` | 传递 planner 上下文 | B - explain conceptually | 自己写一个 `PlannerContextLite`，只保留 `incident` 和 `steps` |
| contextmanager | `src/hz_bank_aiops/storage/task_store.py::_conn` | 管理数据库连接生命周期 | C - debug existing code | 手写一个打印“open/close”的假 context manager |
| Enum | `src/hz_bank_aiops/models/schemas.py::TaskStatus` | 状态流更清晰、更安全 | B - explain conceptually | 把 `NEW/PROCESSING/DONE` 画成状态机 |
| typing / TypedDict | `src/hz_bank_aiops/service/workflow.py::_IncidentState` | LangGraph 状态结构需要明确 | A - recognize only | 解释 `_IncidentState` 里每个字段的作用 |

## 2. FastAPI

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| route decorator | `src/hz_bank_aiops/api/main.py` | 把函数变成 HTTP 接口 | C - debug existing code | 手写一个 `/health` 接口返回固定 JSON |
| request body parsing | `src/hz_bank_aiops/api/main.py::submit_incident` | incident 请求体自动转模型 | C - debug existing code | 自己写一个 `POST /echo` 接收 `name: str` |
| dependency-like singleton | `src/hz_bank_aiops/api/main.py::get_runtime` | 全局 runtime 只初始化一次 | B - explain conceptually | 解释 `@lru_cache` 为什么能减少重复初始化 |

## 3. Pydantic / Data Validation

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| BaseModel | `src/hz_bank_aiops/models/schemas.py` | 统一输入输出结构 | C - debug existing code | 手写一个 `IncidentLite` 模型 |
| model validation | `src/hz_bank_aiops/service/runtime.py::process_one_task` | 任务表里的 payload 要转回强类型对象 | D - modify existing code | 模拟删掉 `hosts` 字段，看哪里报错 |
| Field default_factory | `schemas.py` | 避免列表共享默认值问题 | B - explain conceptually | 解释 `default_factory=list` 和 `=[]` 的差异 |

## 4. RAG

Not used in this repository as a full in-repo RAG pipeline.

Possible reasons:
- 该仓库只保留了 `RagMCPClient`，真正检索在外部 MCP 服务里。

How to verify:
- 看 `src/hz_bank_aiops/mcp/rag_client.py`
- 搜索本仓库是否存在 embedding、vector store、retriever 实现

## 5. Embedding / Vector Store / Retrieval

Not found in repository.

How to verify:
- 没有本地 `embedding.py`、`vector_store.py`、`retriever.py`
- `pyproject.toml` 也没有常见向量库依赖

## 6. Prompt Engineering

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| JSON-only prompting | `src/hz_bank_aiops/agent/react_agent.py::SiliconFlowPlanner._next_action_by_llm` | 希望 LLM 返回结构化动作 | C - debug existing code | 把 prompt 摘出来，解释每一段是在约束什么 |
| tool schema prompting | 同上 | 告诉模型哪些工具可选 | C - debug existing code | 只保留两个工具，重写一版提示词 |

## 7. LangChain

Not used in this repository.

How to verify:
- `pyproject.toml` 没有 langchain 依赖
- 代码中没有 `langchain` import

## 8. LangGraph

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| StateGraph | `src/hz_bank_aiops/service/workflow.py::_build_graph` | 治理流程被建模成图 | B - explain conceptually | 画出 `dedup -> approval -> react` 节点图 |
| conditional edge | 同上 | 不同审批/去重结果走不同路径 | C - debug existing code | 解释 `route_after_approval` 的三个返回值 |
| state update | `src/hz_bank_aiops/agent/langgraph_react.py` | ReAct 版图需要更新 `steps` 和 `memory_summary` | C - debug existing code | 跟着一轮 `plan -> act -> plan` 看状态怎么变 |

## 9. Agent / ReAct / Tool Calling

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| ReAct loop | `src/hz_bank_aiops/agent/react_agent.py::run` | 项目核心诊断逻辑 | F - explain in interview | 自己用 5 句话解释 ReAct 是怎么工作的 |
| planner output | `react_agent.py::LLMAction` | 用结构化形式描述下一步动作 | C - debug existing code | 打印 `action.kind`、`function_call.name` |
| tool observation | `react_agent.py::ToolTraceStep` | 把工具结果反馈给下一步推理 | D - modify existing code | 新增一个 mock tool 并观察 `tool_trace` |

## 10. MCP

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| MCP client role | `src/hz_bank_aiops/mcp/rag_client.py` | 项目通过它调用外部 RAG | B - explain conceptually | 用一句话说明“本项目里的 MCP 是干什么的” |
| tool call payload | `rag_client.py::query` | 请求格式固定为 `name + arguments` | C - debug existing code | 手写一个最小 JSON payload |

## 11. Database / Storage

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| SQLite task queue | `src/hz_bank_aiops/storage/task_store.py::SQLiteTaskStore` | 本地学习最常用路径 | D - modify existing code | 亲手追一次 `enqueue -> claim -> done` |
| PostgreSQL lock strategy | `PostgresTaskStore.claim_next_task` | 生产并发安全关键点 | B - explain conceptually | 解释 `FOR UPDATE SKIP LOCKED` 在解决什么问题 |
| schema initialization | `init_schema` | 保证运行前表存在 | C - debug existing code | 看三张表分别存什么 |

## 12. Async / Concurrency

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| worker polling | `src/hz_bank_aiops/worker/runner.py::run_forever` | 常驻模式会持续拉任务 | B - explain conceptually | 解释为什么没有任务时要 `sleep` |
| in-memory lock | `src/hz_bank_aiops/service/control_center.py` | 去重索引用锁保护 | C - debug existing code | 说明 `_lock` 防止什么问题 |

## 13. Engineering / Deployment / Debugging

| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
| `.env` 配置 | `.env.example`, `config.py` | 运行行为强依赖环境变量 | C - debug existing code | 画出 “配置键 -> 影响模块” 对应表 |
| health endpoint | `api/main.py::health` | 先排环境问题，再排业务问题 | C - debug existing code | 用一段话解释 health 的检查价值 |
| test-driven reading | `tests/test_runtime_flow.py` | 测试是读主链路的捷径 | D - modify existing code | 先读测试，再回头找实现 |
