# Debug Guide

## 1. Run Command
`python main.py`

## 2. Test Input
内置任务：`{"incident_id": "inc_001"}`

## 3. Expected Output
打印三次状态：enqueue 后、claim 后、done 后。

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|
| B1 | `task_store.py` | `enqueue` | `task["status"]` | `NEW` | 看初始状态 |
| B2 | `task_store.py` | `claim` | `task["status"]` | `PROCESSING` | 看认领动作 |
| B3 | `task_store.py` | `mark_done` | `task["status"]` | `DONE` | 看闭环结束 |

## 5. Step-by-Step Debug Path
先看 enqueue，再看 claim，再看 mark_done。

## 6. Common Errors
- claim 时没有过滤 `NEW`
- 更新状态后没写回

## 7. Mapping Back to Original Project
对应 `SQLiteTaskStore.enqueue_incident/claim_next_task/mark_done`。
