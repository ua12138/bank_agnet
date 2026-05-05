# Docker 容器化打包与部署（Dev / Prod）

本文基于当前项目实际代码结构（`src/hz_bank_aiops`）提供三套可执行方案：
- 开发环境：`docker-compose.dev.yml`
- 生产环境：`docker-compose.prod.yml`
- 生产加固：`docker-compose.prod.secure.yml`

## 1. 交付文件

- 镜像构建：`Dockerfile`
- 构建忽略：`.dockerignore`
- 开发编排：`docker-compose.dev.yml`
- 生产编排：`docker-compose.prod.yml`
- 生产加固编排：`docker-compose.prod.secure.yml`
- 生产变量示例：`.env.prod.example`

## 2. 前置条件

1. Docker >= 24，Docker Compose v2
2. 若启用 RAG 工具，需保证 `hz_bank_rag` MCP 服务可达
3. 若启用飞书通知，准备 Webhook URL

## 3. 镜像打包（详细）

### 3.1 本地构建

```powershell
cd D:\code_warehouse\codex_learn\hz_bank_agnet
docker build -t hz-aiops:latest .
```

### 3.2 指定版本标签

```powershell
docker tag hz-aiops:latest hz-aiops:v1.0.0
```

### 3.3 导出为离线包（无仓库环境）

```powershell
docker save -o hz-aiops_v1.0.0.tar hz-aiops:v1.0.0
```

目标机导入：

```powershell
docker load -i hz-aiops_v1.0.0.tar
```

### 3.4 推送到镜像仓库（有仓库环境）

```powershell
docker tag hz-aiops:v1.0.0 <registry>/hz-aiops:v1.0.0
docker push <registry>/hz-aiops:v1.0.0
```

## 4. Dev 部署（开发联调）

特点：
- 暴露 PostgreSQL `5432` 端口，便于本地排查
- API 开启 `uvicorn --reload`
- 挂载源码目录，改代码可快速生效
- 默认开启 CoT 轨迹便于调试

启动：

```powershell
docker compose -f docker-compose.dev.yml up -d --build
```

检查：

```powershell
docker compose -f docker-compose.dev.yml ps
curl http://127.0.0.1:8088/health
```

日志：

```powershell
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f worker
```

停止：

```powershell
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml down -v
```

## 5. Prod 部署（生产）

特点：
- `restart: unless-stopped`
- PostgreSQL 不对外暴露端口
- API/Worker 共用同一镜像标签
- 默认关闭 CoT（降低开销）

### 5.1 准备生产变量

```powershell
copy .env.prod.example .env.prod
```

至少修改：
- `POSTGRES_PASSWORD`
- `IMAGE_TAG`
- `HZ_AIOPS_RAG_MCP_BASE_URL`
- `HZ_AIOPS_FEISHU_WEBHOOK_URL`

### 5.2 启动

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

### 5.3 健康检查

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl http://127.0.0.1:8088/health
```

### 5.4 滚动更新（同机）

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

若不是仓库拉取，而是本机构建新镜像：

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 6. 业务验证（两套环境通用）

### 6.1 提交 incident

```powershell
curl -X POST http://127.0.0.1:8088/api/v1/incidents `
  -H "Content-Type: application/json" `
  -d "{\"incident\":{\"incident_id\":\"inc_docker_001\",\"system\":\"payment-system\",\"service\":\"payment-api\",\"severity\":\"high\",\"event_count\":6,\"window_start\":\"2025-08-01T10:10:00Z\",\"window_end\":\"2025-08-01T10:15:00Z\",\"hosts\":[\"db-prod-01\",\"api-prod-01\"],\"metrics\":[{\"metric\":\"mysql.connections\",\"value\":980}],\"recent_change_ids\":[\"chg_1001\"]},\"priority\":\"P1\"}"
```

### 6.2 查看任务

```powershell
curl http://127.0.0.1:8088/api/v1/tasks
```

## 7. Prod Secure 部署（最小权限加固）

特点：
- API/Worker `read_only: true`
- `tmpfs: /tmp`，避免写入容器层
- `cap_drop: [ALL]`
- `security_opt: no-new-privileges:true`
- `pids_limit / mem_limit / cpus` 资源约束
- 通过 `API_PORT` 控制暴露端口

注意：`docker-compose.prod.secure.yml` 默认只引用镜像，不执行 build。  
因此启动前先确保镜像已存在（本地构建或仓库拉取）。

启动：

```powershell
docker build -t hz-aiops:v1.0.0 .
docker compose --env-file .env.prod -f docker-compose.prod.secure.yml up -d
```

检查：

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.secure.yml ps
curl http://127.0.0.1:8088/health
```

停止：

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.secure.yml down
docker compose --env-file .env.prod -f docker-compose.prod.secure.yml down -v
```

## 8. 常见问题与解决方案

1. 现象：`docker compose` 报 `host.docker.internal` 不可达（Linux 常见）  
解决：把 `HZ_AIOPS_RAG_MCP_BASE_URL` 改为宿主机实际 IP，或将 RAG MCP 也放入 compose 网络。

2. 现象：`/health` 中 `rag_mcp_ok=false`  
解决：确认 `hz_bank_rag` 已启动，端口正确，容器内可访问该地址。

3. 现象：Worker 启动后任务一直 `FAILED`，错误为 payload 字段缺失  
解决：检查 Flink 写入 `payload_json` 是否与 `IncidentPayload` 字段契约一致（`hosts`、`metrics`、`window_start/end` 等）。

4. 现象：`psycopg is required for PostgresTaskStore`  
解决：使用当前 `Dockerfile` 重建镜像，不要复用旧镜像层。

5. 现象：容器可启动但飞书通知失败  
解决：检查 `HZ_AIOPS_FEISHU_WEBHOOK_URL`，以及目标网络是否可访问飞书域名。

6. 现象：本机端口冲突（`8088` 或 `5432`）  
解决：修改 compose 端口映射，例如 `18088:8088`、`15432:5432`。

7. 现象：Windows 下出现 `open C:\\Users\\...\\.docker\\config.json: Access is denied`  
解决：以有权限用户运行 Docker Desktop；必要时修复该文件权限后重试。

8. 现象：数据库卷污染导致历史脏数据影响测试  
解决：执行 `docker compose ... down -v` 清理卷，再重新 `up`。

9. 现象：使用 `docker-compose.prod.secure.yml` 时 API/Worker 无法启动，提示权限或只读文件系统错误  
解决：确认应用未写入非 `/tmp` 路径；如有临时写盘需求，追加 `tmpfs` 挂载点或关闭 `read_only` 后定位具体写入路径。

10. 现象：`docker-compose.prod.secure.yml` 启动时报 `No such image: hz-aiops:<tag>`  
解决：先 `docker build -t hz-aiops:<tag> .`，或修改 `IMAGE_TAG` 为本机已存在标签。

## 9. 安全与生产建议

1. 不要在生产使用默认密码 `aiops`。
2. 生产环境关闭 PostgreSQL 对外端口暴露（已在 prod compose 默认关闭）。
3. 把敏感变量放到安全的 CI/CD Secret 或密钥管理系统，不要明文提交。
4. 若要上公网，请在 API 前增加网关（认证、限流、审计日志）。
