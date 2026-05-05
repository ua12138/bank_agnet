# Debug Guide

## 1. Run Command
`python client.py`

## 2. Test Input
内置 payload：`{"name": "search_manual", "arguments": {"query": "db saturation"}}`

## 3. Expected Output
结构化结果：`{"ok": True, "data": ...}`

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|
| B1 | `client.py` | `main` | `payload` | 包含 `name` 和 `arguments` | 看请求格式 |
| B2 | `server.py` | `handle_call` | `tool_name` | `search_manual` | 看服务端分发 |
| B3 | `tools/search_manual.py` | `search_manual` | `query` | 输入问题 | 看工具处理 |

## 5. Step-by-Step Debug Path
先从 client 组包，再看 server 路由，再进具体 tool。

## 6. Common Errors
- tool name 写错
- `arguments` 缺字段

## 7. Mapping Back to Original Project
对应 `rag_client.py::query` 的 payload 和结果结构。
