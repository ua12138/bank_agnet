# Request / Pipeline Flow

## 1. Selected Main Flow
本项目最值得读的主流程是：
- 主流程 A：`POST /api/v1/incidents` 到任务入队
- 主流程 B：Worker 消费任务并完成诊断

这两个流程组合起来，才是“这个项目真正怎么跑”的完整答案。

## 2. Flow Diagram
```text
Client
  -> POST /api/v1/incidents
  -> api.main.submit_incident
  -> runtime.submit_incident
  -> task_store.enqueue_incident
  -> diagnosis_task(status=NEW)

Worker
  -> runtime.process_one_task
  -> task_store.claim_next_task
  -> workflow.execute
     -> control_center.check_duplicate
     -> control_center.ensure_approval
     -> react_agent / langgraph_react
        -> tool call
        -> observation
        -> final result
  -> task_store.save_result
  -> notifier.send
  -> task_store.mark_done / mark_failed
```

## 3. Step-by-Step Trace

### Step 1: HTTP 请求进入 FastAPI
- Code: `src/hz_bank_aiops/api/main.py::submit_incident`
- Function / class: `submit_incident`
- Input: `IncidentSubmitRequest`
- Output: `{ok, task_id, incident_id}`
- State before: 数据还在 HTTP body 中
- State after: incident 被转成 `IncidentPayload`
- Beginner explanation: 这一层只负责“收参数”和“转发给 runtime”
- Suggested breakpoint: `submit_incident`

### Step 2: runtime 调用存储层入队
- Code: `src/hz_bank_aiops/service/runtime.py::submit_incident`
- Function / class: `DiagnosisRuntime.submit_incident`
- Input: `IncidentPayload`
- Output: `task_id`
- State before: 只有业务对象，没有任务记录
- State after: 任务进入 `diagnosis_task`
- Beginner explanation: runtime 不做复杂逻辑，只把 incident 交给任务表
- Suggested breakpoint: `DiagnosisRuntime.submit_incident`

### Step 3: 任务表写入
- Code: `src/hz_bank_aiops/storage/task_store.py::enqueue_incident`
- Function / class: `SQLiteTaskStore.enqueue_incident` / `PostgresTaskStore.enqueue_incident`
- Input: `payload`, `priority`
- Output: `task_id`
- State before: 任务不存在
- State after: 新增一条 `NEW` 任务
- Beginner explanation: 这一步把“一个事件”变成了“一个待处理任务”
- Suggested breakpoint: `enqueue_incident`

### Step 4: Worker 认领任务
- Code: `src/hz_bank_aiops/service/runtime.py::process_one_task`
- Function / class: `DiagnosisRuntime.process_one_task`
- Input: `worker_id`
- Output: 诊断执行结果或 no pending task
- State before: 存在 `NEW` 任务
- State after: 任务被改成 `PROCESSING`
- Beginner explanation: 这里是异步处理思想的核心，API 只入队，Worker 才真正干活
- Suggested breakpoint: `process_one_task`

### Step 5: 去重检查
- Code: `src/hz_bank_aiops/service/control_center.py::check_duplicate`
- Function / class: `IncidentControlCenter.check_duplicate`
- Input: `IncidentPayload`
- Output: `{is_duplicate, duplicate_of, signature, window_sec}`
- State before: incident 尚未进入治理决策
- State after: 判定是否应该压制重复告警
- Beginner explanation: 如果同一类故障在很短时间内重复出现，不一定要重新诊断
- Suggested breakpoint: `check_duplicate`

### Step 6: 审批检查
- Code: `src/hz_bank_aiops/service/control_center.py::ensure_approval`
- Function / class: `IncidentControlCenter.ensure_approval`
- Input: `IncidentPayload`, `enabled`
- Output: `ApprovalRecord`
- State before: 还没有审批结论
- State after: 可能变成 `pending` / `auto_approved`
- Beginner explanation: 这是“人机协作”环节，不是所有故障都直接跑 Agent
- Suggested breakpoint: `ensure_approval`

### Step 7: ReAct 诊断
- Code: `src/hz_bank_aiops/service/workflow.py::execute`
- Function / class: `IncidentDiagnosisWorkflow.execute`
- Input: `IncidentPayload`
- Output: `DiagnosisResult`
- State before: 只有 incident，没有诊断结论
- State after: 拿到根因、证据、建议和 tool_trace
- Beginner explanation: 这一层负责控制是否进入 Agent，以及 Agent 用哪种执行方式
- Suggested breakpoint: `execute`

### Step 8: 工具调用与 observation
- Code: `src/hz_bank_aiops/agent/react_agent.py::run`
- Function / class: `ReActAgent.run`
- Input: `incident dict`
- Output: `DiagnosisResult`
- State before: `steps=[]`
- State after: `steps` 中记录每一步 `thought/action/observation`
- Beginner explanation: ReAct 就是“想一步、调一个工具、看结果、再想下一步”
- Suggested breakpoint: `run`, `MockOpsPlanner.next_action`, `SiliconFlowPlanner.next_action`

### Step 9: 调用 RAG MCP
- Code: `src/hz_bank_aiops/tools/ops_tools.py::RagCaseTool.run`
- Function / class: `RagCaseTool`
- Input: `incident`
- Output: `{ok, result}` 或 `{ok: False, error}`
- State before: 只掌握本地 observation
- State after: 多了一份外部相似案例信息
- Beginner explanation: 这里不是本地向量库，而是“去问另一个服务”
- Suggested breakpoint: `RagCaseTool.run`, `RagMCPClient.query`

### Step 10: 结果落库与通知
- Code: `src/hz_bank_aiops/service/runtime.py::process_one_task`
- Function / class: `DiagnosisRuntime.process_one_task`
- Input: `DiagnosisResult`
- Output: API/CLI 可见的处理结果
- State before: 结果还在内存里
- State after: `diagnosis_result` 写入，任务标记为 `DONE` 或 `FAILED`
- Beginner explanation: 真正的业务闭环在这里结束
- Suggested breakpoint: `save_result`, `_notify_if_needed`, `mark_done`

## 4. Input / Output Table

| Step | Input | Output |
|---|---|---|
| submit_incident | `IncidentSubmitRequest` | `task_id` |
| enqueue_incident | `payload_json` | `task row` |
| claim_next_task | `worker_id` | `DiagnosisTask` |
| workflow.execute | `IncidentPayload` | `DiagnosisResult` |
| tool.run | `incident` | `observation dict` |
| save_result | `DiagnosisResult` | `result_id` |

## 5. State Changes
- `NEW -> PROCESSING -> DONE`
- 失败路径：`NEW -> PROCESSING -> NEW/FAILED`
- 审批状态：`pending / approved / rejected / auto_approved`
- ReAct 状态：`steps` 逐步累积，LangGraph 路径还会维护 `context_memory`

## 6. Debug Breakpoints
- `api/main.py::submit_incident`
- `service/runtime.py::submit_incident`
- `storage/task_store.py::enqueue_incident`
- `service/runtime.py::process_one_task`
- `service/control_center.py::check_duplicate`
- `service/control_center.py::ensure_approval`
- `service/workflow.py::execute`
- `agent/react_agent.py::run`
- `tools/ops_tools.py::RagCaseTool.run`

## 7. Mapping to Minimal Skeleton
- `mini_fastapi_skeleton` 对应 API -> service
- `mini_storage_skeleton` 对应入队/认领/状态机
- `mini_agent_skeleton` 对应 plan -> tool -> observation -> final
- `mini_langgraph_skeleton` 对应 graph 节点和条件边
- `mini_mcp_skeleton` 对应 client -> tool registry -> result

## 8. Beginner Explanation
你可以把这个项目想成一个“诊断工厂”：
- API 是前台接单员
- 任务表是待办清单
- Worker 是车间工人
- Workflow 是工单审批和流程规则
- Agent 是真正做分析的人
- Tools 是 Agent 手上的诊断工具
- MCP 是外部知识专家
