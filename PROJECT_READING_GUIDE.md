# BANK_AGENT 项目代码精读指南（新手版）

本文面向编程基础较弱的同学，目标是让你先看懂“系统怎么跑起来”，再看懂“请求怎么走完整链路”。

## 1. 项目启动链路

### 1.1 API 服务启动（主入口）
- 文件：`src/hz_bank_aiops/api/main.py`
- 类：`无（函数式路由）`
- 函数：`run()` -> `get_runtime()`

启动顺序：
1. `run()` 启动 Uvicorn。
2. 首次请求触发 `get_runtime()`（`@lru_cache` 单例）。
3. `get_runtime()` 创建 `DiagnosisRuntime` 并调用 `init_schema()` 初始化存储表。

### 1.2 Worker 启动（任务消费入口）
- 文件：`src/hz_bank_aiops/worker/runner.py`
- 类：`WorkerRunner`
- 函数：`run_worker_cli()` -> `run_forever()` / `run_once()`

启动顺序：
1. `run_worker_cli()` 读取配置并创建 `DiagnosisRuntime`。
2. 调用 `runtime.init_schema()` 保证表结构存在。
3. 常驻模式：`run_forever()` 循环调用 `runtime.process_one_task()`。

## 2. 请求调用链路（从告警到结果）

### 2.1 入队阶段
- 文件：`src/hz_bank_aiops/api/main.py`
- 函数：`submit_incident()`
- 下游：`src/hz_bank_aiops/service/runtime.py` 的 `DiagnosisRuntime.submit_incident()`

说明：
- `POST /api/v1/incidents` 接收 `IncidentSubmitRequest`。
- 运行时调用 `store.enqueue_incident()` 把事件写入任务表。

### 2.2 消费与编排阶段
- 文件：`src/hz_bank_aiops/service/runtime.py`
- 类：`DiagnosisRuntime`
- 函数：`process_one_task()`

说明：
1. `claim_next_task(worker_id)` 认领（claim）一条 `NEW` 任务。
2. `IncidentDiagnosisWorkflow.execute()` 执行编排（workflow）。
3. 保存结果 `save_result()`。
4. 视配置发送通知 `_notify_if_needed()`。
5. 成功 `mark_done()`，失败 `mark_failed()`（含重试 retry 策略）。

### 2.3 编排细节（去重 + 审批 + ReAct）
- 文件：`src/hz_bank_aiops/service/workflow.py`
- 类：`IncidentDiagnosisWorkflow`
- 函数：`execute()`、`_execute_classic()`、`_build_graph()`、`_react_diagnose()`

两种引擎：
- `classic`：顺序执行（去重 -> 审批 -> ReAct）。
- `langgraph`：状态图执行（节点路由更清晰）。

## 3. 核心模块职责

### 3.1 运行时装配层
- 文件：`src/hz_bank_aiops/service/runtime.py`
- 类：`DiagnosisRuntime`
- 职责：把存储、RAG 客户端、工具、Agent、编排、通知器组装到一起。

### 3.2 治理中台层
- 文件：`src/hz_bank_aiops/service/control_center.py`
- 类：`IncidentControlCenter`
- 职责：去重（dedup）判断、审批记录管理。

### 3.3 存储层
- 文件：`src/hz_bank_aiops/storage/task_store.py`
- 类：`TaskStore`、`SQLiteTaskStore`、`PostgresTaskStore`
- 职责：任务入队、任务认领、状态变更、结果落库、审批落库。

### 3.4 Agent 与工具层
- 文件：`src/hz_bank_aiops/agent/react_agent.py`
- 类：`ReActAgent`
- 职责：执行 plan -> tool -> observation -> final 推理。

- 文件：`src/hz_bank_aiops/agent/langgraph_react.py`
- 类：`LangGraphReActExecutor`
- 职责：用 LangGraph 管理 ReAct 的状态流和上下文记忆。

- 文件：`src/hz_bank_aiops/tools/ops_tools.py`
- 职责：封装运维工具调用（供 Agent 使用）。

### 3.5 外部集成层
- 文件：`src/hz_bank_aiops/mcp/rag_client.py`
- 类：`RagMCPClient`
- 职责：调用 RAG MCP 服务获取诊断辅助信息。

- 文件：`src/hz_bank_aiops/notifier/feishu.py`
- 类：`FeishuNotifier`
- 职责：发送飞书通知。

## 4. 框架在本项目中的实际作用

- FastAPI：定义 API 路由与请求模型。关键文件：`src/hz_bank_aiops/api/main.py`。
- Pydantic：校验输入输出数据结构。关键文件：`src/hz_bank_aiops/models/schemas.py`。
- LangGraph：可选编排引擎；管理节点、路由、状态。关键文件：`src/hz_bank_aiops/service/workflow.py`、`src/hz_bank_aiops/agent/langgraph_react.py`。
- SQLite/PostgreSQL：任务队列与结果存储。关键文件：`src/hz_bank_aiops/storage/task_store.py`。
- Flink SQL：上游告警聚合与落库脚本（离线/流式侧）。关键目录：`flinksql/`。

## 5. ASCII 架构图

```text
          +---------------------+
          |   Flink SQL / Data  |
          +----------+----------+
                     |
                     v
+-----------+   +----+--------------------+   +------------------+
|   Client  +-->+ FastAPI(api/main.py)    +-->+ DiagnosisRuntime |
+-----------+   +----+--------------------+   +----+------+------+ 
                                                    |      |
                                                    |      +-------------------+
                                                    v                          v
                                      +-------------+-----------+    +---------+--------+
                                      | IncidentDiagnosisWorkflow|    | FeishuNotifier   |
                                      +-------------+-----------+    +------------------+
                                                    |
                                                    v
                                      +-------------+-----------+
                                      | ReActAgent / LangGraph  |
                                      +-------------+-----------+
                                                    |
                                                    v
                                      +-------------+-----------+
                                      | TaskStore(SQLite/PG)    |
                                      +-------------------------+
```

## 6. ASCII 请求调用链路图

```text
POST /api/v1/incidents
  -> api.main.submit_incident
  -> runtime.submit_incident
  -> task_store.enqueue_incident

Worker loop
  -> worker.runner.run_forever
  -> runtime.process_one_task
     -> task_store.claim_next_task
     -> workflow.execute
        -> control_center.check_duplicate
        -> control_center.ensure_approval
        -> react_agent/langgraph_react
     -> task_store.save_result
     -> notifier.send (optional)
     -> task_store.mark_done / mark_failed
```

## 7. 不确定项

- `LangGraph` 在你当前运行环境是否一定可用：**不确定**。代码中存在 `classic` 降级路径（`src/hz_bank_aiops/service/runtime.py` 的 `__init__`）。
- 上游 Flink 到本服务的生产接入方式是否已全量打通：**不确定**（需结合部署环境验证）。
