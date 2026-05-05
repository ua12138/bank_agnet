# Mini Skeleton Plan

## mini_fastapi_skeleton

### Learning Goal
理解 `request body -> schema -> router -> service -> response` 这一条最基础的 Web 路径。

### Original Project Mapping
- `src/hz_bank_aiops/api/main.py`
- `src/hz_bank_aiops/models/schemas.py`
- `src/hz_bank_aiops/service/runtime.py`

### File Structure
```text
learning_skeletons/mini_fastapi_skeleton/
  main.py
  schemas.py
  routers/chat.py
  services/chat_service.py
  README.md
  DEBUG_GUIDE.md
```

### Run Command
`python learning_skeletons/mini_fastapi_skeleton/main.py`

### Debug Points
- 请求体什么时候变成 Python 对象
- router 和 service 的职责边界

### Hand-Code Tasks
- 自己加一个 `GET /health`
- 把返回结果改成包含 `trace`

### Completion Standard
能说清楚“API 入口只收参，真正逻辑在 service”

## mini_agent_skeleton

### Learning Goal
理解 ReAct：为什么要 `plan -> tool -> observation -> final`

### Original Project Mapping
- `src/hz_bank_aiops/agent/react_agent.py`
- `src/hz_bank_aiops/tools/ops_tools.py`

### File Structure
```text
learning_skeletons/mini_agent_skeleton/
  main.py
  agent.py
  state.py
  prompts.py
  tools/
```

### Run Command
`python learning_skeletons/mini_agent_skeleton/main.py`

### Debug Points
- planner 决策输出
- tool observation 怎样影响下一步

### Hand-Code Tasks
- 增加一个 `db_tool`
- 改 planner 顺序

### Completion Standard
能解释每一步 observation 为什么会改变下一步行动

## mini_langgraph_skeleton

### Learning Goal
理解“图编排”不是魔法，本质是“状态 + 节点函数 + 条件跳转”。

### Original Project Mapping
- `src/hz_bank_aiops/service/workflow.py`
- `src/hz_bank_aiops/agent/langgraph_react.py`

### File Structure
```text
learning_skeletons/mini_langgraph_skeleton/
  main.py
  graph.py
  state.py
  nodes/
```

### Run Command
`python learning_skeletons/mini_langgraph_skeleton/main.py`

### Debug Points
- 当前状态对象
- 下一跳路由结果

### Hand-Code Tasks
- 自己加一个 `approval` 分支
- 增加一个 `duplicate` 快速结束分支

### Completion Standard
能手画节点图，并说明每个节点输入输出

## mini_mcp_skeleton

### Learning Goal
理解本项目里 MCP 的角色：客户端发起工具调用，请求外部服务返回结构化结果。

### Original Project Mapping
- `src/hz_bank_aiops/mcp/rag_client.py`
- `src/hz_bank_aiops/tools/ops_tools.py::RagCaseTool`

### File Structure
```text
learning_skeletons/mini_mcp_skeleton/
  server.py
  client.py
  tools/search_manual.py
```

### Run Command
`python learning_skeletons/mini_mcp_skeleton/client.py`

### Debug Points
- payload 的 `name` 和 `arguments`
- 序列化结果结构

### Hand-Code Tasks
- 增加一个 `tool not found` 分支
- 让 client 调另一个工具

### Completion Standard
能解释“为什么本项目不在本仓库直接做 RAG，而是去调外部 MCP”

## mini_storage_skeleton

### Learning Goal
理解任务表是怎样把“一个 incident”变成“一个可消费任务”的。

### Original Project Mapping
- `src/hz_bank_aiops/storage/task_store.py`
- `src/hz_bank_aiops/service/runtime.py::process_one_task`

### File Structure
```text
learning_skeletons/mini_storage_skeleton/
  main.py
  task_store.py
  models.py
```

### Run Command
`python learning_skeletons/mini_storage_skeleton/main.py`

### Debug Points
- enqueue 后状态
- claim 后状态
- done / failed 后状态

### Hand-Code Tasks
- 增加 retry 次数
- 模拟失败回退

### Completion Standard
能画出 `NEW -> PROCESSING -> DONE/FAILED` 状态机
