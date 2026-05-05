# ACCEPTANCE

## 1. 验收目标
覆盖以下能力并提供可复现步骤：
- FlinkSQL 产物齐全（source、聚合、任务落库、Doris 落库）
- 诊断任务调度可运行（SQLite/PostgreSQL）
- LangGraph 工作流可运行（告警去重、人工审批、ReAct）
- 飞书 Webhook 通知链路可调用
- 能调用同级 `hz_bank_rag` 的 MCP 服务
- `tests/` 组件级验证通过
- `demotest/` 最小化链路可跑通

## 2. 环境准备
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[langgraph]
copy .env.example .env
```

可选（用于验证 RAG MCP 联通）：
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
.\scripts\start_mcp.ps1 -Port 8091
```

## 3. 主链路验收（API + Worker）
1. 启动 API：
```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.api.main
```
2. 健康检查：`GET /health`，确认字段：
- `task_db_kind`
- `workflow_engine`
- `resolved_workflow_engine`
- `rag_mcp_ok`
3. 提交 incident：`POST /api/v1/incidents`
4. 执行一次消费：`POST /api/v1/workers/run-once`
5. 查看任务状态：`GET /api/v1/tasks`

## 4. 人工审批验收
1. 设置：`HZ_AIOPS_ENABLE_HUMAN_APPROVAL=true`
2. 提交 `high/critical` 等需要审批的 incident
3. 首次消费期望结果为 pending（诊断等待审批）
4. 调用：`POST /api/v1/approvals/{incident_id}` 提交 `approved`
5. 再次执行 worker，进入正式诊断并写入结果表

## 5. 飞书通知验收
1. 设置：`HZ_AIOPS_FEISHU_WEBHOOK_URL=...`
2. 运行 worker 消费任务
3. 期望 `notify_status` 为：
- webhook 可达：`SENT`
- webhook 不可达：`FAILED`

## 6. FlinkSQL 验收
检查文件完整性与可部署性：
- `flinksql/01_sources.sql`
- `flinksql/02_incident_aggregation.sql`
- `flinksql/03_task_sink_postgres.sql`
- `flinksql/04_doris_sink.sql`

检查样例数据：
- `data/sample/zabbix_alerts.jsonl`
- `data/sample/xuelang_changes.jsonl`
- `data/sample/incidents.json`

## 7. 组件级测试验收
```powershell
set PYTHONPATH=src
python -m unittest discover -s tests -v
```
期望：全部测试通过。

## 8. demotest 最小链路验收
启动：
```powershell
python -m uvicorn demotest.app.main:app --port 8098 --reload
```

按 `demotest/docs/RUNBOOK.md` 执行：
1. `POST /demo/seed`
2. `POST /demo/run-once`
3. `GET /demo/results`

期望：
- 返回可见 ReAct reasoning 过程
- 包含 `metric_probe/change_probe/rag_probe`
- 当 `hz_bank_rag` MCP 已启动时，`rag_probe.observation.ok=true`

## 9. 常见失败与排查
1. `ModuleNotFoundError`：
- 执行 `pip install -e .`
2. `LangGraph` 不可用：
- 执行 `pip install -e .[langgraph]`
- 或设置 `HZ_AIOPS_WORKFLOW_ENGINE=classic`
3. `rag_probe` 失败：
- 确认 `hz_bank_rag` MCP 已启动在 `http://127.0.0.1:8091`
4. worker 无任务：
- 确认已调用 incident 入队接口

## 10. 对应文档
- 详细开发规格：`docs/spec/DEV_SPEC.md`
- OpenAPI：`docs/spec/openapi.yaml`
- 镜像验收文档：`docs/spec/ACCEPTANCE.md`
- demotest 调试手册：`docs/demotest/RUNBOOK.md`
