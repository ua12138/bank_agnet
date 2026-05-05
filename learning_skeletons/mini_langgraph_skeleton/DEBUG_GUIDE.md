# Debug Guide

## 1. Run Command
`python main.py`

## 2. Test Input
内置 state：`{"duplicate": False, "approved": True}`

## 3. Expected Output
看到节点执行顺序：`plan -> tool -> final`

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|
| B1 | `graph.py` | `run_graph` | `current` | 节点名变化 | 看图是怎么跳的 |
| B2 | `nodes/plan_node.py` | `plan_node` | `state["history"]` | 增加记录 | 看状态更新 |
| B3 | `nodes/final_node.py` | `final_node` | `state["result"]` | 最终答案 | 看结束点 |

## 5. Step-by-Step Debug Path
先在 `graph.py` 看跳转，再进入节点函数查看 state 修改。

## 6. Common Errors
- 忘记返回下一节点名
- 修改了 state 但没有返回

## 7. Mapping Back to Original Project
对应 `workflow.py::_build_graph` 的节点函数和条件边。
