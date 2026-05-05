# ACCEPTANCE（新手可执行版）

本文是 BANK_AGENT 项目的验收步骤清单，目标是让你按步骤确认：
1. API 能启动
2. Worker 能消费任务
3. 诊断结果能落库
4. 审批/通知链路可验证

## 1. 环境准备

在项目根目录执行：

```powershell
cd d:\CodeWarehouse\CodexLearn\bank_agnet
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[langgraph]
copy .env.example .env
```

说明：
- `pip install -e .` 会安装基础依赖（含 `httpx`）。
- `pip install -e .[langgraph]` 会安装 LangGraph 可选依赖。
- 如果你只想走经典流程，可在 `.env` 设置：`HZ_AIOPS_WORKFLOW_ENGINE=classic`。

## 2. 启动与健康检查

### 2.1 启动 API

```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.api.main
```

### 2.2 健康检查

访问：`GET /health`

至少确认这些字段存在：
- `task_db_kind`
- `workflow_engine`
- `resolved_workflow_engine`
- `rag_mcp_ok`

## 3. 主链路验收（入队 -> 消费 -> 结果）

1. 提交 incident：`POST /api/v1/incidents`
2. 触发一次 worker：`POST /api/v1/workers/run-once`
3. 查询任务列表：`GET /api/v1/tasks`
4. 预期：新任务状态从 `NEW` 进入 `PROCESSING`，最终到 `DONE` 或 `FAILED`

## 4. 审批链路验收（可选）

1. `.env` 中开启：`HZ_AIOPS_ENABLE_HUMAN_APPROVAL=true`
2. 提交一个需要审批的高等级 incident
3. 首次消费预期得到 `pending` 结果
4. 调用：`POST /api/v1/approvals/{incident_id}` 提交 `approved`
5. 再触发 worker，预期进入正式诊断流程

## 5. 通知链路验收（可选）

1. 配置：`HZ_AIOPS_FEISHU_WEBHOOK_URL=...`
2. 消费任务后检查 `notify_status`

预期：
- webhook 可达：`SENT`
- webhook 不可达：`FAILED`

## 6. 测试验收

```powershell
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

如果出现依赖错误：
- `No module named 'httpx'`：重新执行 `pip install -e .`
- `No module named 'langgraph'`：执行 `pip install -e .[langgraph]`

## 7. demotest 最小链路验收

```powershell
python -m uvicorn demotest.app.main:app --port 8098 --reload
```

按 `docs/demotest/RUNBOOK.md` 依次调用：
1. `POST /demo/seed`
2. `POST /demo/run-once`
3. `GET /demo/results`

## 8. 关键文档入口

- 项目阅读导图：`PROJECT_READING_GUIDE.md`
- 代码注释规范：`docs/CODE_COMMENT_GUIDE.md`
- OpenAPI：`docs/spec/openapi.yaml`
- 开发规格：`docs/spec/DEV_SPEC.md`
