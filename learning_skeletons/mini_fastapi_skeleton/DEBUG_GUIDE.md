# Debug Guide

## 1. Run Command
`python main.py`

## 2. Test Input
内置 `{"question": "what is task queue?"}`

## 3. Expected Output
返回一个字典，包含 `question` 和 `answer`。

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|
| B1 | `schemas.py` | `ChatRequest.__init__` | `question` | 非空字符串 | 理解请求对象的起点 |
| B2 | `routers/chat.py` | `chat` | `request.question` | 与输入一致 | 理解 router 只转发 |
| B3 | `services/chat_service.py` | `answer_question` | `answer` | 字符串 | 理解业务逻辑在 service |

## 5. Step-by-Step Debug Path
先看 `main.py` 如何构造请求，再进 `routers/chat.py`，最后看 `services/chat_service.py`。

## 6. Common Errors
- Import error：没有在 skeleton 目录运行
- 路由逻辑写太重：把业务塞进了 router

## 7. Mapping Back to Original Project
这个骨架对应 `api/main.py::submit_incident` 到 runtime 的“入口分层”思想。
