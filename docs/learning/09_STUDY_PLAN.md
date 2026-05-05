# Study Plan

## 1. Study Goal
目标不是背文件名，而是做到三件事：
- 能画出主链路
- 能自己 debug 一次主链路
- 能在面试里完整解释项目价值与边界

## 2. 7-Day Minimum Plan
### Day 1
- 读 `00_EXECUTIVE_SUMMARY.md`
- 读 `01_PROJECT_MAP.md`
- 打开 `api/main.py` 和 `runtime.py`

### Day 2
- 读 `02_STARTUP_FLOW.md`
- 跑 `mini_fastapi_skeleton`
- 解释 `router -> service`

### Day 3
- 读 `03_REQUEST_FLOW.md`
- 读 `storage/task_store.py`
- 跑 `mini_storage_skeleton`

### Day 4
- 读 `workflow.py`
- 读 `control_center.py`
- 跑 `mini_langgraph_skeleton`

### Day 5
- 读 `react_agent.py`
- 读 `ops_tools.py`
- 跑 `mini_agent_skeleton`

### Day 6
- 读 `rag_client.py`
- 跑 `mini_mcp_skeleton`
- 完成 `07_QUESTION_BANK.md` 前 10 题

### Day 7
- 读 `08_FINAL_PROJECT_REVIEW.md`
- 用自己的话复述项目
- 对照 `06_MASTERY_TRACKER.md` 自评

## 3. 14-Day Standard Plan
- 第 1-7 天按上面执行
- 第 8 天读 `demotest/app/main.py`
- 第 9 天读 `tests/test_runtime_flow.py`
- 第 10 天读 `tests/test_task_store.py`
- 第 11 天复盘 `langgraph_react.py`
- 第 12 天尝试改一个 skeleton
- 第 13 天做完整问答自测
- 第 14 天做一次 3 分钟面试讲解

## 4. Daily Output Checklist
- 画 1 张流程图
- 记 3 个函数名
- 解释 2 个状态变化
- 完成 1 个 skeleton 或 1 组问题
- 写 1 段“今天我真正懂了什么”

## 5. What to Ask ChatGPT After Each Day
- “请用更白话解释今天这 3 个函数”
- “请出 5 道只围绕今天内容的题”
- “请把今天的链路图纠错”

## 6. What to Ask Codex After Each Day
- “带我走一遍这个函数的断点调试”
- “帮我对照 skeleton 和原项目做映射”
- “请检查我对主流程的理解哪里还不准”
