# Debug Guide

## 1. Run Command
`python main.py`

## 2. Test Input
内置 incident：数据库连接数过高。

## 3. Expected Output
看到 `steps` 中依次出现 `metric_tool`、`change_tool`、`case_search_tool`。

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|
| B1 | `agent.py` | `next_action` | `done_actions` | 集合逐步变大 | 看 planner 如何决策 |
| B2 | `agent.py` | `run` | `tool_name` | 依次变化 | 看工具调用顺序 |
| B3 | `agent.py` | `run` | `steps` | 长度递增 | 看 observation 如何累积 |

## 5. Step-by-Step Debug Path
先断在 planner 决策，再进工具函数，再回到主循环看 `steps`。

## 6. Common Errors
- 把最终答案提前返回，导致没有完整 observation
- 新增工具但忘记放进 `tools` 注册表

## 7. Mapping Back to Original Project
对应 `react_agent.py::run` 和 `MockOpsPlanner.next_action`。
