# ACCEPTANCE（中文验收说明）

## 1. 验收目标
覆盖：
- FlinkSQL 产物齐全
- 任务调度（SQLite/PostgreSQL）可运行
- LangGraph 工作流（去重/审批/ReAct）可执行
- 飞书通知链路可用
- RAG MCP 工具可调用同级 `hz_bank_rag`
- tests 通过
- demotest 最小链路跑通

## 2. 环境准备
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[langgraph]
copy .env.example .env
```

若需要验证 RAG MCP：
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
.\scripts\start_mcp.ps1 -Port 8091
```

## 3. API 验收
1. 启动 API：
```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.api.main
```
2. `GET /health` 返回 `task_db_kind/workflow_engine/rag_mcp_ok`
3. `POST /api/v1/incidents` 成功入队
4. `POST /api/v1/workers/run-once` 完成一条任务诊断
5. `GET /api/v1/tasks` 可看到状态变化

## 4. 审批验收（开启审批）
1. 设置 `HZ_AIOPS_ENABLE_HUMAN_APPROVAL=true`
2. 提交 high/critical incident
3. 第一次处理返回 pending 结果
4. `POST /api/v1/approvals/{incident_id}` 提交 approved
5. 再次执行 worker，任务可进入正式诊断

## 5. 飞书通知验收
1. 配置 `HZ_AIOPS_FEISHU_WEBHOOK_URL`
2. 运行 worker
3. 任务 `notify_status` 应为 `SENT`（不可达时为 `FAILED`）

## 6. FlinkSQL 验收
检查以下文件是否完整并可用于部署：
- `flinksql/01_sources.sql`
- `flinksql/02_incident_aggregation.sql`
- `flinksql/03_task_sink_postgres.sql`
- `flinksql/04_doris_sink.sql`

检查样例数据：
- `data/sample/zabbix_alerts.jsonl`
- `data/sample/xuelang_changes.jsonl`
- `data/sample/incidents.json`

## 7. tests 验收
执行：
```powershell
set PYTHONPATH=src
python -m unittest discover -s tests -v
```
期望：全部通过。

## 8. demotest 验收
执行：
```powershell
python -m uvicorn demotest.app.main:app --port 8098 --reload
```
然后按 `demotest/docs/RUNBOOK.md`：
1. `/demo/seed`
2. `/demo/run-once`
3. `/demo/results`

文档镜像路径：`docs/demotest/RUNBOOK.md`

期望：
- 可看到完整 reasoning 轨迹
- reasoning 中 `rag_probe` 有返回（RAG MCP 启动时）

## 9. 失败排查
1. `rag_probe` 失败：先确认 `hz_bank_rag` MCP 是否启动
2. Worker 无任务：确认是否执行了入队接口
3. LangGraph 初始化失败：安装 `pip install -e .[langgraph]` 或启用 fallback
4. 飞书失败：检查 webhook 可达性和企业网络策略
