# DEV_SPEC（开发规格，中文教学版）

## 1. 文档目的
本文面向开发与维护同学，说明项目分层、数据流、状态流与关键配置，帮助你定位问题和扩展功能。

## 2. 分层结构
- 接口层（API）：`src/hz_bank_aiops/api/main.py`
- 运行时装配层（Runtime）：`src/hz_bank_aiops/service/runtime.py`
- 治理与编排层（Control + Workflow）：
  - `src/hz_bank_aiops/service/control_center.py`
  - `src/hz_bank_aiops/service/workflow.py`
- 推理层（Agent）：
  - `src/hz_bank_aiops/agent/react_agent.py`
  - `src/hz_bank_aiops/agent/langgraph_react.py`
- 存储层（Store）：`src/hz_bank_aiops/storage/task_store.py`
- 工具与外部集成层：
  - `src/hz_bank_aiops/tools/ops_tools.py`
  - `src/hz_bank_aiops/mcp/rag_client.py`
  - `src/hz_bank_aiops/notifier/feishu.py`

## 3. 数据与状态流

### 3.1 任务流
1. API 入队：`submit_incident()` -> `enqueue_incident()`
2. Worker 认领：`claim_next_task()`
3. 诊断执行：`workflow.execute()`
4. 结果落库：`save_result()`
5. 状态收敛：`mark_done()` 或 `mark_failed()`

### 3.2 任务状态机
- `NEW`：待消费
- `PROCESSING`：处理中
- `DONE`：完成
- `FAILED`：失败

重试规则：`retry_count < max_retry` 时，失败任务可回退到 `NEW`。

## 4. 编排模型

### 4.1 classic
顺序流程：`dedup -> approval -> react`

### 4.2 langgraph
同样的业务逻辑以状态图表达：
- 节点：`dedup`、`approval`、`react`
- 分支：`duplicate`、`pending`、`rejected`、`approved`

若 LangGraph 依赖不可用且允许降级，则回退 `classic`。

## 5. ReAct 与工具调用
- planner 决定下一步工具。
- 工具返回 observation（成功或失败都会记录）。
- 达成收敛后输出 `DiagnosisResult`。

默认工具集：
- `zabbix_realtime_metrics`
- `doris_history_lookup`
- `xuelang_change_lookup`
- `rag_case_search`

## 6. 关键配置
- 引擎：`HZ_AIOPS_WORKFLOW_ENGINE=langgraph|classic`
- 去重窗口：`HZ_AIOPS_DEDUP_WINDOW_SEC`
- 审批开关：`HZ_AIOPS_ENABLE_HUMAN_APPROVAL`
- RAG MCP 地址：`HZ_AIOPS_RAG_MCP_BASE_URL`
- CoT：`HZ_AIOPS_REACT_COT_*`
- 上下文记忆：`HZ_AIOPS_REACT_MEMORY_*`

## 7. 验收与测试
- 主验收文档：`docs/ACCEPTANCE.md`
- 单元测试：`python -m unittest discover -s tests -v`
- 最小链路：`demotest/` + `docs/demotest/RUNBOOK.md`

## 8. 常见故障定位
- `ModuleNotFoundError: httpx`：执行 `pip install -e .`
- `ModuleNotFoundError: langgraph`：执行 `pip install -e .[langgraph]`
- `rag_probe` 失败：确认 RAG MCP 服务已启动且地址可达。
- Worker 无任务：先确认 `/api/v1/incidents` 已成功入队。
