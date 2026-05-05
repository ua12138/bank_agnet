# Question Bank

## 1. Basic Understanding

### Q1. 这个项目的核心业务目标是什么？
- Type: Basic understanding
- Related code: `src/hz_bank_aiops/api/main.py`, `src/hz_bank_aiops/service/runtime.py`
- Expected answer: 接收 incident，创建任务，Worker 消费任务，经治理和 ReAct 诊断得到根因与建议。
- What a weak answer misses: 只说“这是一个 FastAPI 项目”，没有说 Worker、任务表、Agent。
- Scoring: 2 分说出 API，3 分说出 Worker，5 分说出完整闭环。

### Q2. 为什么这个项目不是“用户请求来就直接调用 Agent”？
- Type: Architecture
- Related code: `storage/task_store.py`, `worker/runner.py`
- Expected answer: 项目采用入队 + Worker 消费模式，方便异步处理、重试和状态追踪。
- What a weak answer misses: 没提任务状态和失败重试。
- Scoring: 5 分必须提到任务表和 Worker。

### Q3. `DiagnosisRuntime` 在项目中扮演什么角色？
- Type: Code reading
- Related code: `service/runtime.py::DiagnosisRuntime`
- Expected answer: 它负责装配存储、MCP 客户端、tools、Agent、workflow、notifier，是主运行入口。
- What a weak answer misses: 把它误解成“只是一层 service”。
- Scoring: 3 分说出装配，5 分说出具体依赖。

## 2. Code Reading

### Q4. `POST /api/v1/incidents` 到底走到了哪里？
- Type: Code reading
- Related code: `api/main.py::submit_incident`, `runtime.py::submit_incident`, `task_store.py::enqueue_incident`
- Expected answer: 先进入路由，再进入 runtime，最后写入任务表。
- What a weak answer misses: 少了一层或把 runtime 和 storage 混为一谈。
- Scoring: 5 分需要说完整三步。

### Q5. `process_one_task()` 为什么是最关键的函数？
- Type: Code reading
- Related code: `service/runtime.py::process_one_task`
- Expected answer: 它串起 claim、workflow、save_result、notify、mark_done/failed。
- What a weak answer misses: 没说这是实际消费任务的核心。
- Scoring: 5 分需要说出至少四个子步骤。

### Q6. `workflow.execute()` 和 `agent.run()` 的职责差别是什么？
- Type: Architecture
- Related code: `service/workflow.py::execute`, `agent/react_agent.py::run`
- Expected answer: workflow 负责治理流程，agent 负责诊断推理。
- What a weak answer misses: 把两者都当成“推理”。
- Scoring: 5 分要区分治理和推理。

### Q7. `check_duplicate()` 为什么不放到 Agent 里？
- Type: Architecture
- Related code: `service/control_center.py::check_duplicate`
- Expected answer: 去重是治理规则，不是模型推理问题。
- What a weak answer misses: 不理解“确定性规则”和“LLM 推理”的分层。
- Scoring: 5 分。

## 3. Debugging

### Q8. 如果 `GET /health` 里 `planner_mode` 是 `mock`，说明什么？
- Type: Debugging
- Related code: `service/runtime.py::health`
- Expected answer: 没有成功启用硅基流动 LLM，当前在走本地 fallback planner。
- What a weak answer misses: 只说“LLM 没工作”，没说降级逻辑。
- Scoring: 5 分。

### Q9. 如果任务始终停留在 `NEW`，先看哪里？
- Type: Debugging
- Related code: `worker/runner.py`, `runtime.py::process_one_task`
- Expected answer: 先确认 Worker 是否启动，再看 `claim_next_task()` 是否被调用。
- What a weak answer misses: 直接怀疑数据库或 API。
- Scoring: 5 分。

### Q10. `rag_probe` 或 `rag_case_search` 失败时，系统会怎样？
- Type: Debugging
- Related code: `tools/ops_tools.py::RagCaseTool.run`, `mcp/rag_client.py::query`
- Expected answer: 会记录错误 observation，但主流程不一定立刻崩溃。
- What a weak answer misses: 以为 RAG 失败就一定整个任务失败。
- Scoring: 5 分。

## 4. Implementation

### Q11. 如果你要加一个新工具，应该从哪里开始？
- Type: Implementation
- Related code: `tools/base.py`, `tools/ops_tools.py`, `react_agent.py`
- Expected answer: 先定义 tool，再加入 `build_default_tools()`，必要时调整 planner。
- What a weak answer misses: 只想到改 planner，没想到注册工具。
- Scoring: 5 分。

### Q12. 如果你要把审批条件从高危故障改成“某个 service 也必须审批”，改哪？
- Type: Implementation
- Related code: `service/control_center.py::ensure_approval`
- Expected answer: 先改治理规则，而不是改 Agent。
- What a weak answer misses: 改错层。
- Scoring: 5 分。

### Q13. 如果要支持另一种通知渠道，最合理的入口在哪里？
- Type: Implementation
- Related code: `notifier/feishu.py`, `runtime.py::_notify_if_needed`
- Expected answer: 在 notifier 层扩展，然后 runtime 决定是否调用。
- What a weak answer misses: 直接在 workflow 里硬编码发通知。
- Scoring: 5 分。

## 5. Architecture

### Q14. 为什么项目同时保留 `classic` 和 `langgraph` 两种 workflow？
- Type: Architecture
- Related code: `service/workflow.py`, `service/runtime.py`
- Expected answer: 提供依赖降级与可选复杂度，LangGraph 不可用时能退回 classic。
- What a weak answer misses: 只说“为了兼容”，没有说运行时 fallback。
- Scoring: 5 分。

### Q15. 为什么本仓库没有本地完整 RAG，却仍然说和 RAG 有关？
- Type: Architecture
- Related code: `mcp/rag_client.py`, `tools/ops_tools.py::RagCaseTool.run`
- Expected answer: 因为它通过 MCP 客户端调用外部 RAG 服务，本仓库只保留调用侧。
- What a weak answer misses: 把 RAG 和 MCP 混成一件事。
- Scoring: 5 分。

## 6. Interview Explanation

### Q16. 用 1 分钟解释这个项目。
- Type: Interview explanation
- Related code: `api/main.py`, `runtime.py`, `workflow.py`
- Expected answer: “这是一个 AIOps 事件诊断服务，上游 incident 入队，Worker 消费任务，经去重、审批和 ReAct 诊断生成根因与建议，还能调用外部 RAG MCP 做案例辅助。”
- What a weak answer misses: 只讲了框架名，没有讲业务闭环。
- Scoring: 5 分。

### Q17. 这个项目里 Agent 的价值是什么？
- Type: Interview explanation
- Related code: `agent/react_agent.py`, `tools/ops_tools.py`
- Expected answer: 让系统根据已收集证据动态决定下一步工具，而不是完全写死固定脚本。
- What a weak answer misses: 把 Agent 说成“只是大模型接口”。
- Scoring: 5 分。

### Q18. 你不能夸大说这个项目支持什么？
- Type: Interview explanation
- Related code: `pyproject.toml`, `mcp/rag_client.py`
- Expected answer: 不能夸大说它内置完整向量数据库、本地 embedding 流程、分布式调度器或 LangChain。
- What a weak answer misses: 不区分“外部服务调用”和“仓库内实现”。
- Scoring: 5 分。

## 7. Self-Test Scoring Rubric
- 0-30：只能认文件，不能讲链路
- 31-60：能讲主流程，但不能 debug
- 61-80：能 debug 主流程，能解释架构
- 81-100：能画图、能手写 skeleton、能做面试复述
