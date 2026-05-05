# 代码中文注释说明

## 1. 本次补充范围
本次已为以下核心代码补充中文注释，且不改变业务逻辑：

- `src/hz_bank_aiops/config.py`
- `src/hz_bank_aiops/models/schemas.py`
- `src/hz_bank_aiops/storage/factory.py`
- `src/hz_bank_aiops/storage/task_store.py`
- `src/hz_bank_aiops/service/control_center.py`
- `src/hz_bank_aiops/service/workflow.py`
- `src/hz_bank_aiops/service/runtime.py`
- `src/hz_bank_aiops/agent/react_agent.py`
- `src/hz_bank_aiops/agent/langgraph_react.py`
- `src/hz_bank_aiops/tools/base.py`
- `src/hz_bank_aiops/tools/ops_tools.py`
- `src/hz_bank_aiops/mcp/rag_client.py`
- `src/hz_bank_aiops/notifier/feishu.py`
- `src/hz_bank_aiops/api/main.py`
- `src/hz_bank_aiops/worker/runner.py`
- `scripts/run_worker_once.py`
- `scripts/seed_incidents.py`
- `demotest/app/*.py`（main/worker/react_tools/db/settings）

## 2. 注释风格约定
- 模块级注释：说明该文件在整条链路中的职责。
- 类/函数注释：解释输入输出、关键副作用与异常处理策略。
- 关键分支注释：只针对复杂逻辑（去重、审批、重试、降级、并发抢占）添加。
- 不添加“翻译式废话注释”，避免噪声。

## 3. 重点链路注释位置
- Flink 下游任务消费：`worker/runner.py`、`service/runtime.py`
- 编排层（去重/审批/ReAct）：`service/workflow.py`、`service/control_center.py`
- ReAct 推理环：`agent/react_agent.py`、`agent/langgraph_react.py`
- 工具调用与外部集成：`tools/ops_tools.py`、`mcp/rag_client.py`、`notifier/feishu.py`
- 持久化与重试语义：`storage/task_store.py`

## 4. 后续维护建议
- 新增模块时，至少包含 1 段模块注释 + 公开函数注释。
- 任何状态机/重试/并发逻辑变更，必须同步更新对应注释。
- 当注释与代码不一致时，以代码为准并立即修注释。
