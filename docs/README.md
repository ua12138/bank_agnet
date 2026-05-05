# Bank AIOps Incident Diagnosis Platform

基于 Flink + Doris + LLM Agent 的智能运维事件诊断平台完整代码实现。

## 1. 功能范围
- Flink 阶段 SQL（告警接入、聚合、Incident 归并、任务落库、Doris 落库）
- Worker + 任务表调度（SQLite/PostgreSQL）
- LangGraph 工作流（去重 + 人工审批 + ReAct）
- LangGraph ReAct 执行器（plan -> tool -> observation -> final）
- 飞书 Webhook 通知
- RAG MCP 调用（同级 `hz_bank_rag` 项目）
- 组件级 tests
- demotest 最小可验证链路

## 2. 目录结构
```text
.
├─ src/hz_bank_aiops/
│  ├─ api/
│  ├─ agent/
│  ├─ mcp/
│  ├─ models/
│  ├─ notifier/
│  ├─ service/
│  ├─ storage/
│  ├─ tools/
│  └─ worker/
├─ flinksql/
├─ sql/
├─ data/sample/
├─ tests/
├─ demotest/
│  ├─ app/
│  └─ docs/
└─ docs/
   ├─ spec/
   └─ demotest/
```

## 3. 安装
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[langgraph]
```

## 4. 配置
复制并修改：
```powershell
copy .env.example .env
```

重点配置：
- `HZ_AIOPS_TASK_DB_KIND=sqlite|postgres`
- `HZ_AIOPS_SQLITE_PATH=./data/runtime/diagnosis.db`
- `HZ_AIOPS_POSTGRES_DSN=...`（仅 postgres 时）
- `HZ_AIOPS_WORKFLOW_ENGINE=langgraph|classic`
- `HZ_AIOPS_FEISHU_WEBHOOK_URL=...`
- `HZ_AIOPS_RAG_MCP_BASE_URL=http://127.0.0.1:8091`

## 5. API 启动
```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.api.main
```

默认端口 `8088`，核心接口：
- `GET /health`
- `POST /api/v1/incidents`
- `GET /api/v1/tasks`
- `POST /api/v1/workers/run-once`
- `GET /api/v1/approvals/{incident_id}`
- `POST /api/v1/approvals/{incident_id}`
- `GET /api/v1/rag/health`

## 6. Worker 启动
单次消费：
```powershell
set PYTHONPATH=src
python scripts\run_worker_once.py
```

常驻消费：
```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.worker.runner
```

## 7. 样例入队
```powershell
set PYTHONPATH=src
python scripts\seed_incidents.py
```

## 8. FlinkSQL 交付
见 `flinksql/`：
- `01_sources.sql`
- `02_incident_aggregation.sql`
- `03_task_sink_postgres.sql`
- `04_doris_sink.sql`

样例输入：`data/sample/`

## 9. 运行测试
```powershell
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

## 10. demotest 最小化验证
```powershell
python -m uvicorn demotest.app.main:app --port 8098 --reload
```

详见：`docs/demotest/RUNBOOK.md`

## 11. 文档
- 总体规格：`docs/spec.md`
- 开发规格：`docs/spec/DEV_SPEC.md`
- 验收说明：`docs/ACCEPTANCE.md`
- OpenAPI：`docs/spec/openapi.yaml`
- 项目导读：`docs/PROJECT_READING_GUIDE.md`
- LangGraph ReAct CoT：`docs/spec/LANGGRAPH_REACT_COT.md`
- LangGraph Sliding Context + Dynamic Memory：`docs/spec/LANGGRAPH_CONTEXT_MEMORY.md`
- Docker 部署（dev/prod/secure）：`docs/DOCKER_DEPLOY.md`
