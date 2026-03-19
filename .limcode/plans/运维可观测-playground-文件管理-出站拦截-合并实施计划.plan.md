## TODO LIST

<!-- LIMCODE_TODO_LIST_START -->
- [ ] 在 routes/admin.py 加 apply_backend_log_preferences 调用  `#s1-admin-hook`
- [ ] 在 routes/stats.py 新增 /v1/backend_logs 端点  `#s1-backend-logs-api`
- [ ] 新增 BackendLogs.tsx 前端页面  `#s1-frontend-page`
- [ ] App.tsx 和 Layout.tsx 加路由和导航  `#s1-frontend-route`
- [ ] 替换 core/log_config.py 为带后台日志采集的版本  `#s1-log-config`
- [ ] 在 main.py lifespan 加 apply_backend_log_preferences 调用  `#s1-main-hook`
- [ ] 新增 routes/health.py 健康检查端点  `#s2-health`
- [ ] main.py 补充 app.state 字段并注册 health router  `#s2-main-health`
- [ ] 新增 core/watchdog.py 轻量事件循环监控  `#s2-watchdog`
- [ ] 新增 core/http.py 统一出站请求拦截  `#s3-http-trace`
- [ ] 在 core/log_config.py 末尾触发 http trace 安装  `#s3-install-hook`
- [ ] 暴露出站请求记录的 API 端点  `#s3-outbound-api`
- [ ] 新增 playgroundAttachments.ts  `#s4-attachments`
- [ ] package.json 新增 katex 依赖  `#s4-katex`
- [ ] 新增 MarkdownRenderer.tsx  `#s4-markdown`
- [ ] 替换 Playground.tsx  `#s4-playground`
- [ ] 新增 routes/workspace.py 文件管理后端  `#s5-workspace-api`
- [ ] 新增 Workspace.tsx 文件管理前端  `#s5-workspace-page`
- [ ] 注册 workspace 路由和导航  `#s5-workspace-route`
<!-- LIMCODE_TODO_LIST_END -->

# 合并实施计划

## 第 1 步：后台日志系统

### 后端
- 替换 `core/log_config.py`：重写为带 TeeStream + BackendCaptureStreamHandler + 内存环形缓冲区的版本
- 在 `routes/stats.py` 新增 `GET /v1/backend_logs` 端点，调用 `get_backend_log_entries()`
- 在 `routes/admin.py` 的 `api_config_update` 末尾加 `apply_backend_log_preferences()` 调用
- 在 `main.py` lifespan 中配置加载后调用 `apply_backend_log_preferences()`

### 前端
- 新增 `frontend/src/pages/BackendLogs.tsx`
- `frontend/src/App.tsx` 加 `/backend-logs` 路由
- `frontend/src/components/Layout.tsx` 加导航项

## 第 2 步：健康检查 + 轻量 watchdog

### 后端
- 新增 `core/watchdog.py`（轻量 sleep 漂移检测 + 快照）
- 新增 `routes/health.py`（`/healthz` + `/readyz`，不经过 /v1 前缀和认证）
- `routes/__init__.py` 注册 health router
- `main.py` lifespan 中补充 `started_at`、`startup_completed`、`version` 字段，启动轻量 watchdog
- 保留现有 `core/block_watchdog.py` 不变

## 第 3 步：统一出站请求拦截记录

### 后端
- 新增 `core/http.py`：monkey-patch `httpx.AsyncClient.__init__`，自动注入 event_hooks 记录所有出站请求
- 在 `core/log_config.py` 末尾 `import core.http` 触发安装
- 在 `/v1/backend_logs` 端点或新增 `/v1/outbound_logs` 端点暴露出站记录

### 前端
- BackendLogs 页面增加出站请求 tab，或新建独立页面

## 第 4 步：Playground 改进

### 前端
- 新增 `frontend/src/lib/playgroundAttachments.ts`
- 新增 `frontend/src/components/MarkdownRenderer.tsx`
- 替换 `frontend/src/pages/Playground.tsx`
- `frontend/package.json` 新增 `katex` + `@types/katex` 依赖

## 第 5 步：文件管理界面

### 后端
- 新增 `routes/workspace.py`（白名单目录浏览/读写/删除/下载）
- `routes/__init__.py` 注册 workspace router

### 前端
- 新增 `frontend/src/pages/Workspace.tsx`
- `frontend/src/App.tsx` 加路由
- `frontend/src/components/Layout.tsx` 加导航项

## 注意事项
- `core/log_config.py` 是全项目最早加载的模块，替换需确保接口兼容（`from core.log_config import logger` 不变）
- 健康检查端点不走 /v1 前缀，不需要认证
- 出站拦截通过 monkey-patch httpx.AsyncClient.__init__ 实现，零改动覆盖所有出站请求
- Playground.tsx 变化太大，整体替换而非 diff 合并
- 文件管理界面需要严格白名单控制可访问路径
