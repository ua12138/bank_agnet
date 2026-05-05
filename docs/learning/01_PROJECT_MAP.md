# Project Map

## 1. One-Sentence Positioning
这是一个“面向运维事件诊断”的 Python 服务：FastAPI 负责收任务，Worker 负责消费任务，Agent 负责诊断，MCP 客户端负责调用外部 RAG 服务。

## 2. Technology Stack
- Python 3.10+
- FastAPI
- Pydantic / pydantic-settings
- httpx
- LangGraph（可选依赖）
- SQLite / PostgreSQL
- Flink SQL（上游任务生成，不在 Python 主运行时内）

## 3. Directory Structure
```text
src/hz_bank_aiops/
  api/         FastAPI 入口
  service/     运行时、治理、编排
  agent/       ReAct 与 LangGraph ReAct
  storage/     任务/结果/审批存储
  tools/       指标、历史、变更、RAG 工具
  mcp/         RAG MCP 客户端
  notifier/    飞书通知
  models/      Pydantic 数据模型
  worker/      Worker CLI 与轮询

demotest/
  app/         最小演示版 API / worker / pseudo react

flinksql/
  上游 SQL 样例

tests/
  核心行为测试
```

## 4. Core Modules

| Module | Responsibility | Important Files | Runtime Role | Beginner Priority |
|---|---|---|---|---|
| API | 对外暴露 HTTP 路由 | `src/hz_bank_aiops/api/main.py` | 收 incident、查任务、提审批 | P0 - must read first |
| Runtime | 装配所有依赖 | `src/hz_bank_aiops/service/runtime.py` | 主运行入口 | P0 - must read first |
| Workflow | 去重、审批、ReAct 编排 | `src/hz_bank_aiops/service/workflow.py` | 治理流程核心 | P0 - must read first |
| Agent | 决定调用什么工具、如何收敛结果 | `src/hz_bank_aiops/agent/react_agent.py` | 诊断推理核心 | P1 - read after main flow |
| LangGraph Agent | 用图方式执行 ReAct | `src/hz_bank_aiops/agent/langgraph_react.py` | 进阶路径 | P1 - read after main flow |
| Storage | 任务/结果/审批持久化 | `src/hz_bank_aiops/storage/task_store.py` | 状态与数据落地 | P1 - read after main flow |
| Control Center | 去重和审批策略 | `src/hz_bank_aiops/service/control_center.py` | 治理中台 | P1 - read after main flow |
| Tools | 诊断用外部/模拟工具 | `src/hz_bank_aiops/tools/ops_tools.py` | 生成 observation | P1 - read after main flow |
| MCP Client | 调 RAG 服务 | `src/hz_bank_aiops/mcp/rag_client.py` | 外部知识调用 | P2 - read after skeleton is understood |
| Notifier | 发飞书通知 | `src/hz_bank_aiops/notifier/feishu.py` | 结果发送 | P2 - read after skeleton is understood |
| DemoTest | 教学简化版 | `demotest/app/main.py` | 最小验证链路 | P0 - must read first |

## 5. Runtime Entry Points
- API 入口：`src/hz_bank_aiops/api/main.py::run`
- Worker 入口：`src/hz_bank_aiops/worker/runner.py::run_worker_cli`
- 单次消费脚本：`scripts/run_worker_once.py::main`
- 样例入队脚本：`scripts/seed_incidents.py::main`
- Demo API：`demotest/app/main.py::run`

## 6. Configuration and Environment
- 配置类：`src/hz_bank_aiops/config.py::Settings`
- 关键配置：
  - `HZ_AIOPS_WORKFLOW_ENGINE`
  - `HZ_AIOPS_TASK_DB_KIND`
  - `HZ_AIOPS_SQLITE_PATH`
  - `HZ_AIOPS_POSTGRES_DSN`
  - `HZ_AIOPS_ENABLE_HUMAN_APPROVAL`
  - `HZ_AIOPS_RAG_MCP_BASE_URL`
  - `HZ_AIOPS_LLM_PROVIDER`
  - `HZ_AIOPS_LLM_API_KEY`

## 7. External Services and Dependencies
- 外部 RAG MCP 服务：通过 `GET /health`、`POST /tools/call` 调用。  
  Code: `src/hz_bank_aiops/mcp/rag_client.py::health`  
  Code: `src/hz_bank_aiops/mcp/rag_client.py::query`
- 飞书 webhook：Code: `src/hz_bank_aiops/notifier/feishu.py`
- PostgreSQL：生产存储后端。  
- SQLite：默认本地学习/调试后端。

## 8. Data Objects and Domain Objects
- 输入事件：`IncidentPayload`
- 任务：`DiagnosisTask`
- 结果：`DiagnosisResult`
- 工具轨迹：`ToolTraceStep`
- 审批记录：`ApprovalRecord`
- 任务认领结果：`TaskClaimResult`  
Code: `src/hz_bank_aiops/models/schemas.py`

## 9. Main Runtime Objects
- `DiagnosisRuntime`
- `IncidentDiagnosisWorkflow`
- `IncidentControlCenter`
- `ReActAgent`
- `LangGraphReActExecutor`
- `SQLiteTaskStore` / `PostgresTaskStore`
- `RagMCPClient`

## 10. Dependency Direction
```text
api -> service.runtime
service.runtime -> storage / workflow / tools / notifier / mcp
workflow -> control_center / agent
agent -> tools
tools -> mcp
worker -> service.runtime
```

## 11. Beginner Reading Order
1. `demotest/app/main.py`
2. `src/hz_bank_aiops/api/main.py`
3. `src/hz_bank_aiops/service/runtime.py`
4. `src/hz_bank_aiops/service/workflow.py`
5. `src/hz_bank_aiops/agent/react_agent.py`
6. `src/hz_bank_aiops/storage/task_store.py`
7. `src/hz_bank_aiops/service/control_center.py`
8. `src/hz_bank_aiops/tools/ops_tools.py`

## 12. Files to Temporarily Ignore
- `docker-compose*.yml`
- `flinksql/*.sql`
- `sql/postgres_schema.sql`
- `docs/spec/*.md`
- `tests/test_langgraph_react_*`（第二轮再读）
