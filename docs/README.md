# Bank AIOps Incident Diagnosis Platform

基于 Flink + Doris + LLM Agent 的智能运维事件诊断平台。

## 快速理解
- API 入口：`src/hz_bank_aiops/api/main.py`
- 运行时装配：`src/hz_bank_aiops/service/runtime.py`
- 编排层：`src/hz_bank_aiops/service/workflow.py`
- 存储层：`src/hz_bank_aiops/storage/task_store.py`
- Worker：`src/hz_bank_aiops/worker/runner.py`

## 启动方式

### 1) 安装
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[langgraph]
```

### 2) 配置
```powershell
copy .env.example .env
```

### 3) 启动 API
```powershell
set PYTHONPATH=src
python -m hz_bank_aiops.api.main
```

### 4) 启动 Worker（单次）
```powershell
set PYTHONPATH=src
python scripts\run_worker_once.py
```

### 5) 注入样例 incident
```powershell
set PYTHONPATH=src
python scripts\seed_incidents.py
```

## 文档导航
- 新手导读：`PROJECT_READING_GUIDE.md`
- 开发规范：`docs/spec/DEV_SPEC.md`
- OpenAPI：`docs/spec/openapi.yaml`
- 部署文档：`docs/DOCKER_DEPLOY.md`
