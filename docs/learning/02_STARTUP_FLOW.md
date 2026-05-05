# Startup Flow

## 1. Startup Commands
- API:
  - `set PYTHONPATH=src`
  - `python -m hz_bank_aiops.api.main`
- Worker:
  - `set PYTHONPATH=src`
  - `python -m hz_bank_aiops.worker.runner --once`
- Demo:
  - `python -m uvicorn demotest.app.main:app --port 8098 --reload`

## 2. Environment Requirements
- Python >= 3.10
- 基础依赖：`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`
- 若使用 LangGraph：需要安装 `langgraph`
- 若使用 PostgreSQL：需要可用的 `psycopg`

## 3. Process Startup Sequence

### Step 1: 运行模块入口
- Code: `src/hz_bank_aiops/api/main.py::run`
- Input: Python 模块启动命令
- Output: Uvicorn 进程
- What happens: 通过 `uvicorn.run()` 启动 FastAPI 应用。
- Beginner explanation: 这是“把 Python 文件变成 Web 服务”的那一步。
- Debug observation: 看 `host`、`port`、`app` 字符串是否正确。

### Step 2: FastAPI app 对象创建
- Code: `src/hz_bank_aiops/api/main.py::app`
- Input: 路由函数定义
- Output: `FastAPI` 实例
- What happens: 框架收集后续的 `@app.get` / `@app.post` 路由。
- Beginner explanation: 你可以把 `app` 理解成“这个服务的大门”。
- Debug observation: 检查 `title`、`version` 是否存在。

### Step 3: 第一次请求触发 runtime 创建
- Code: `src/hz_bank_aiops/api/main.py::get_runtime`
- Input: 无
- Output: `DiagnosisRuntime`
- What happens: 用 `@lru_cache` 保证只创建一份运行时对象。
- Beginner explanation: 运行时里装着数据库、工作流、Agent、通知器这些核心部件。
- Debug observation: 首次请求时会执行 `runtime.init_schema()`。

### Step 4: 读取配置
- Code: `src/hz_bank_aiops/config.py::get_settings`
- Input: `.env` / 环境变量
- Output: `Settings`
- What happens: 加载 DB、workflow、LLM、MCP、worker 等配置。
- Beginner explanation: 不同环境的行为，大多从这里决定。
- Debug observation: `workflow_engine`, `task_db_kind`, `llm_api_key`, `rag_mcp_base_url`

### Step 5: 运行时装配
- Code: `src/hz_bank_aiops/service/runtime.py::DiagnosisRuntime.__init__`
- Input: `Settings`
- Output: `DiagnosisRuntime`
- What happens:
  - 创建 `TaskStore`
  - 创建 `RagMCPClient`
  - 构建 `tools`
  - 构建 `ReActAgent`
  - 构建 `IncidentControlCenter`
  - 构建 `IncidentDiagnosisWorkflow`
  - 构建 `FeishuNotifier`
- Beginner explanation: 这一层不是业务逻辑，而是“把零件装起来”。
- Debug observation: `resolved_workflow_engine`, `agent.planner_mode`

## 4. FastAPI App Creation
- Code: `src/hz_bank_aiops/api/main.py`
- App 对象在模块导入时就创建。
- 实际业务依赖在 `get_runtime()` 中延迟初始化。
- 这种写法能避免启动时做太多重活。

## 5. Router Registration
- `GET /health`
- `POST /api/v1/incidents`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/workers/run-once`
- `GET /api/v1/approvals/{incident_id}`
- `POST /api/v1/approvals/{incident_id}`
- `GET /api/v1/rag/health`

## 6. Service / Chain / Agent Initialization
- 业务服务核心：`DiagnosisRuntime`
- 工作流核心：`IncidentDiagnosisWorkflow`
- 推理核心：`ReActAgent`
- LangGraph 路径：`LangGraphReActExecutor`
- 降级规则：`langgraph` 不可用时，可退回 `classic`

## 7. External Resource Initialization
- SQLite 文件路径：`Settings.sqlite_path_obj`
- PostgreSQL：`PostgresTaskStore`
- RAG MCP：`RagMCPClient(base_url=...)`
- 飞书 webhook：`FeishuNotifier`

## 8. Minimum Startup Path
最小可学习路径：
1. 使用 SQLite
2. 使用 `classic` workflow
3. 不依赖真实飞书
4. 不依赖真实 RAG
5. 用 `demotest` 或 `scripts/seed_incidents.py` 触发链路

## 9. Startup Debug Points
- `api/main.py::get_runtime`
- `config.py::get_settings`
- `service/runtime.py::DiagnosisRuntime.__init__`
- `storage/task_store.py::SQLiteTaskStore.init_schema`
- `service/workflow.py::IncidentDiagnosisWorkflow.__init__`

## 10. Common Startup Errors
- `ModuleNotFoundError: hz_bank_aiops`
  - 原因：`PYTHONPATH=src` 未设置
- `ModuleNotFoundError: httpx`
  - 原因：基础依赖未安装
- `ModuleNotFoundError: langgraph`
  - 原因：可选依赖未安装
- `RuntimeError: psycopg is required`
  - 原因：切到 PostgreSQL 但没装驱动
