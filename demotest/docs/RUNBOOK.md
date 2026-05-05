# DemoTest 运行调试手册

## 1. 目标
验证最小化完整链路：
1. FastAPI 接收伪 incident
2. SQLite task 表入队
3. 伪 worker 执行降格 ReAct（metrics/change/rag）
4. 输出 reasoning 过程
5. 调用同级 `hz_bank_rag` 的 MCP 服务

## 2. 前置条件
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

可选：在 `.env` 增加 demotest RAG 参数（默认已可用）
```dotenv
HZ_AIOPS_DEMO_RAG_MCP_BASE_URL=http://127.0.0.1:8091
HZ_AIOPS_DEMO_RAG_TIMEOUT_SEC=60
HZ_AIOPS_DEMO_RAG_QUERY_TOP_K=1
HZ_AIOPS_DEMO_RAG_CANDIDATE_MULTIPLIER=1
HZ_AIOPS_DEMO_RAG_FAST_MODE=true
HZ_AIOPS_DEMO_RAG_USE_MEMORY=false
```

可选：启动同级 RAG MCP（用于验证 rag 调用成功）
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
.\scripts\start_mcp.ps1 -Port 8091
```

## 3. 启动 demotest API
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
python -m uvicorn demotest.app.main:app --port 8098 --reload
```

## 4. 调试流程

### 4.1 健康检查
`GET http://127.0.0.1:8098/health`

### 4.2 注入伪输入任务
`POST http://127.0.0.1:8098/demo/seed`

### 4.3 触发伪 worker 运行一次
`POST http://127.0.0.1:8098/demo/run-once`

返回应包含：
- `summary`
- `reasoning[]`
- `reasoning[*].action = metric_probe/change_probe/rag_probe`

### 4.4 查看任务表
`GET http://127.0.0.1:8098/demo/tasks`

### 4.5 查看结果表
`GET http://127.0.0.1:8098/demo/results`

## 5. 验证 RAG 调用成功
在 `/demo/run-once` 响应里检查：
- `reasoning` 中 `action=rag_probe`
- `observation.ok=true`
- 当前协议已统一为：`POST /tools/call` + `name` + `arguments`
- 若 RAG 服务未配置 SiliconFlow Key，会自动降级为 `rag.list_documents`（`observation.mode=rag.list_documents`）
- 若已配置 Key，则执行 `rag.query`（`observation.mode=rag.query`）

若为 `false`，检查：
1. `hz_bank_rag` MCP 是否已启动
2. 地址是否为 `http://127.0.0.1:8091`
3. 网络与端口策略是否阻断
4. 查看 `observation.error`，定位具体失败原因
5. 若需强制验证 `rag.query`，确认 `HZ_RAG_SILICONFLOW_API_KEY` 已配置并重启 MCP
6. 若 `observation.error` 包含 `timed out`，增大 `HZ_AIOPS_DEMO_RAG_TIMEOUT_SEC`（建议 90~120）后重启 demotest

## 6. 常见问题
1. `ModuleNotFoundError: fastapi`：执行 `pip install -e .`
2. `rag_probe connection refused`：MCP 未启动
3. SQLite 文件锁：关闭多余测试进程后重试
