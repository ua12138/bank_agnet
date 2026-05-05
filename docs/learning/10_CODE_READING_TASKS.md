# Code Reading Tasks

## 1. P0 Tasks - Main Flow

### Task 1: 从 API 到任务表
- Read: `src/hz_bank_aiops/api/main.py`, `src/hz_bank_aiops/service/runtime.py`, `src/hz_bank_aiops/storage/task_store.py`
- Goal: 弄清楚 incident 是怎样变成任务的
- Questions to answer:
  - 谁接收 HTTP body？
  - 谁创建 task？
  - task 初始状态是什么？
- Debug action: 在 `submit_incident` 和 `enqueue_incident` 设断点
- Completion standard: 能不用看代码复述三步链路

### Task 2: 从 Worker 到诊断结果
- Read: `src/hz_bank_aiops/worker/runner.py`, `src/hz_bank_aiops/service/runtime.py`
- Goal: 弄清楚任务是怎样被消费的
- Questions to answer:
  - `run_once()` 和 `run_forever()` 有什么区别？
  - `process_one_task()` 串了哪些步骤？
- Debug action: 观察 `claim`, `task`, `result`
- Completion standard: 能画出消费闭环

## 2. P1 Tasks - Core Modules

### Task 3: 去重和审批
- Read: `src/hz_bank_aiops/service/control_center.py`
- Goal: 理解确定性治理逻辑
- Questions to answer:
  - signature 怎么构造？
  - 哪些严重级别自动审批？
- Debug action: 观察 `duplicate_of`, `status`
- Completion standard: 能解释为什么这部分不该交给 LLM

### Task 4: Workflow 编排
- Read: `src/hz_bank_aiops/service/workflow.py`
- Goal: 理解 classic 与 langgraph 的关系
- Questions to answer:
  - 哪些情况直接返回？
  - 哪些情况进入 Agent？
- Debug action: 在 `route_after_dedup` 和 `route_after_approval` 设断点
- Completion standard: 能画出条件分支图

### Task 5: ReAct 核心
- Read: `src/hz_bank_aiops/agent/react_agent.py`
- Goal: 理解 planner、tool、observation、final
- Questions to answer:
  - `LLMAction` 是什么？
  - `ToolTraceStep` 为什么重要？
- Debug action: 观察 `action.kind`, `tool_name`, `observation`
- Completion standard: 能解释一次完整 ReAct 循环

## 3. P2 Tasks - Supporting Modules

### Task 6: MCP 外部调用
- Read: `src/hz_bank_aiops/mcp/rag_client.py`, `src/hz_bank_aiops/tools/ops_tools.py`
- Goal: 理解本仓库如何借外部 RAG
- Questions to answer:
  - payload 格式是什么？
  - 调用失败时怎么返回？
- Debug action: 观察 `payload`, `resp.json()`, `error`
- Completion standard: 能解释“这里不是本地 RAG”

### Task 7: demotest 教学路径
- Read: `demotest/app/main.py`, `demotest/app/worker.py`, `demotest/app/react_tools.py`
- Goal: 用简化版理解原项目
- Questions to answer:
  - 哪些模块是缩小版？
  - 哪些逻辑被简化了？
- Debug action: 跑 `/demo/seed` -> `/demo/run-once`
- Completion standard: 能说出 demotest 对应原项目哪里

## 4. P3 Tasks - Optional / Later

### Task 8: Flink 与 SQL
- Read: `flinksql/*.sql`, `sql/postgres_schema.sql`
- Goal: 理解 incident 是如何形成和落库的
- Questions to answer:
  - 为什么 Python 服务没有直接处理原始告警？
  - diagnosis_task 表字段怎么来的？
- Debug action: 对照 schema 看 SQL 输出字段
- Completion standard: 能把“上游 incident 生成”讲清楚

## 5. Verification Tasks
- 用自己的话解释 `DiagnosisRuntime`
- 手画 `NEW -> PROCESSING -> DONE/FAILED`
- 手画 `dedup -> approval -> react`
- 说明 MCP 在这个仓库里的角色
- 说明 LangGraph 在这个仓库里的角色

## 6. Refuse-to-Overclaim Checklist
- 我不能说仓库内实现了完整 RAG 检索链，除非我能指出 embedding 和 vector store 代码。
- 我不能说项目用了 LangChain，除非我能指出 `langchain` 依赖和 import。
- 我不能说这个项目一定会调用真实 LLM，除非确认 `planner_mode` 不是 `mock`。
- 我不能说工具都是真实生产系统，除非确认它不是 mock 返回。
