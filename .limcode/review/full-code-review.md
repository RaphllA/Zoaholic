# Zoaholic 全量代码审查
- Date: 2026-03-18
- Overview: 针对端核心链路、路由层、前端台与新合并的可观测性/工作区功能进行全量审查。
- Status: completed
- Overall decision: needs_follow_up

## Review Scope
Zoaholic 全量代码审查

- 日期：2025-02-14
- 范围：后端核心模块、路由层、前端页面与基础设施配置
- 方法：按模块增量审查，并在每个阶段记录结论与风险

### 初始结论
已完成对当前工作区核心后端、路由层、前端控制台与新增可观测性/工作区功能的全量审查。代码整体结构清晰，启动链路、日志采集、前端页面与基本鉴权都已联通，但当前仍存在不适合直接忽略的上线风险：出站请求拦截未覆盖失败路径，工作区白名单超出约束并暴敏感文件，功能凭证传递方式错误，前端鉴请求链路也尚未完全收敛。综合判断，当前更适“修复后复审”而非直接视为完全通过。

## Review Summary
<!-- LIMCODE_REVIEW_SUMMARY_START -->
- Current status: completed
- Reviewed modules: main.py, core/http.py, core/log_config.py, core/watchdog.py, routes/health, routes/stats.py, routes/workspace.py, frontend/src/pages/Workspace.tsxcore/auth.py, routes/__init__.py, frontend/src/lib/api.ts, frontend/src/pages/Dashboard.tsx, frontend/src/pages/Logs.tsx, frontend/src/pages/Login.tsxfrontend/src/pages/Setup.tsx, test/, core/test/
- Current progress: 3 milestones recorded; latest: m3-frontend-session-tests
- Total milestones: 3
- Completed milestones: 3
- Total findings: 6
- Findings by severity: high 2 / medium 3 / low 1
- Latest conclusion: 已完成对当前工作区核心后端、路由层、前端控制台与新增可观测性/工作区功能的全量审查。代码整体结构清晰，启动链路、日志采集、前端页面与基本鉴权都已联通，但当前仍存在不适合直接忽略的上线风险：出站请求拦截未覆盖失败路径，工作区白名单超出约束并暴敏感文件，功能凭证传递方式错误，前端鉴请求链路也尚未完全收敛。综合判断，当前更适“修复后复审”而非直接视为完全通过。
- Recommended next action: 优先修复四项上线前问题：1) 补齐 outbound failure logging；2) 收缩 workspace 白名单并移除 `.env` 等敏感路径；3) 重做 workspace 下载鉴权4) 统一 `/1/*` 请求到 apiFetch，然后再补最小回归测试后复审。
- Overall decision: needs_follow_up
<!-- LIMCODE_REVIEW_SUMMARY_END -->

## Review Findings
<!-- LIMCODE_REVIEW_FINDINGS_START -->
- [high] other: 出站 HTTP 拦截不会连接失败/超时类请求
  - ID: F-001
  - Description: `core/http.py` 只在 `_on_response` 中把请求写入缓冲区，而 `httpx` 的 response hook 仅在成功收到响应后才会触发。像ConnectError`、`ReadTimeout`、TLS 握手失败、DNS 失败等场景虽然是最需要排查的出站故障，但当前实现不会留下任何记录，因此与“捕获全部出站请求”的设计目标不一致。
  - Evidence Files:
    - `core/http.py`
    - `main.py`
    - `core/log_config.py`
    - `core/watchdog.py`
    - `routes/health.py`
    - `routes/stats.py`
  - Related Milestones: m1-runtime-observability
  - Recommendation: 在 request hook 中先生成一条 pending 记录，或包装 transport/发送调用，在异常路径也写入失败条目（包含异常类型、目标 host、耗时、状态=transport_error 等）。

- [medium] maintainability: healthz 与 readyz 没有真正区分存活和就绪义
  - ID: F-002
  - Description: `routes/health.py` 的 `__health_payload` 接 `read` 参数，但内部完全没有使用它，导致 `/healthz` 和 `/readyz` 返回相同的状态码与检查逻辑。这样会让外部针无法区分“进程还活着”与“服务已经准备接流量”，在启动/退化阶段容易产生错误的编排行为。
  - Evidence Files:
    - `routes/health.py`
    - `main.py`
    - `core/http.py`
    - `core/log_config.py`
    - `core/watchdog.py`
    - `routes/stats.py`
  - Related Milestones: m1-runtime-observability
  - Recommendation: 明确拆分探针职责：`/healthz` 只反映进程存活与事件循环是否完全失控，`readyz` 再额外检查配置、client_manager、channel_manager、startup_completed 等就绪条件。

- [high] accessibility: 工作区白名单超出既定范围并暴露敏感配置文件
  - ID: -003
  - Description: 需求约束明确要求工作区严格限制在 `api.yaml`、`data/`、`plugins/`。但 `routes/workspace.py` 的 `WORKSPACE_RULES` 额外放开了 `.env`、`pyproject.toml`、`docker-compose.yml`、`Dockerfile`、`docs/ 等路径，其中 `.env` 可能包含真实凭证或运行时秘密。即便接口是 admin-only，这依属于安全边界扩大和需求偏离。
  - Evidence Files:
    - `routes/workspace.py`
    - `frontend/src/pages/Workspace.tsx`
    - `core/auth.py`
    - `routes/__init__.py`
  - Related Milestones: m2-workspace-security
  - Recommendation: 将白名单收缩回明确要求的三类路径；如果确有运维需求，改为单独的受控 capability 开关，并对 `.env` 这类秘密文件默认永久禁用。

- [medium] javascript: 工作区下载功能通过 URL 暴露 token 且与后端鉴权方式不兼容
  - ID: -004
  - Description: 前端 `Workspacex` 用 `window.open('/v1/workspace/download?...&token=...')` 触发下载，但 `core/auth.py` 的 `_admin_api_key` 只从 `Authorization` 或 `x-api-key` 头里取 token，不读取 query 参数。因此下载功能在当前实现会直接 403；同时把 JWT 拼进 URL 还会进入浏览器历史、反向代理日志和监控系统，造成不必要的凭证暴露。
  - Evidence Files:
    - `routes/workspace.py`
    - `frontend/src/pages/Workspace.tsx`
    - `core/auth.py`
    - `routes/__init__.py`
  - Related Milestones: m2-workspace-security
  - Recommendation: 改为使用带 `Authorization` 头的 `fetch/blob` 下载，或在后端提供一次性短时下载票据，不要把长期 JWT 放进查询串。

- [medium] javascript: 管理台仍混用原生 fetch 与 apiFetch，导致 JWT 失效处理不一致
  - ID: F-005
  - Description: `frontend/src/lib.ts` 已封装本地鉴权失败后的统一 `logout + 跳转登录页` 辑，但 `.tsx`、`Logs.tsx` 等页面仍直接对 `/v1/*`用原生 `fetch`。这会使部分页面在 JWT 失效后继续停留在当前页面、只表现为静默失败或局部报错，而另一些页面会正确到登录页，形成不一致的会话体验。
  - Evidence Files:
    - `frontend/src/lib/api.ts`
    - `frontend/src/pages/Dashboardx`
    - `frontend/src/pages/Logs.tsx`
    - `frontend/src/pages/Dashboard.tsx`
    - `frontend/src/pages/Logsx`
    - `frontend/src/pages/Login.tsx`
    - `/src/pagesSetup.tsx`
    - `test/`
    - `core/test/`
  - Related Milestones: m3-frontend-session-tests
  - Recommendation: 将需要管理端鉴权的 `/v1/*` 请求统一收敛到 `apiFetch`，并为少数需要特殊处理的页面提供显式 opt-out 注释，而不是继续混用两套请求方式。

- [low] test: 新增可观测性与工作区功能缺少自动化覆盖
  - ID: F-新增可观测性与工作区功能缺少自动化覆盖
  - Description: 针对 `workspace`、`backend_logs、`outbound_logs`、`healthz`、`readyz` 的关键路径 `test/` 与 `core/test/` 中均未找到对应测试由于这些功能同时涉及鉴权、文件边界、健康探针和 monkey-patch，缺乏回归测试会后续重构风险明显偏。
  - Evidence Files:
    - `test/`
    - `core/test/`
    - `routesspace.py`
    - `routes/stats.py`
    - `routes/health.py`
    - `core/http.py`
    - `frontend/src/lib/api.ts`
    - `frontend/src/pages/Dashboard.tsx`
    - `frontend/src/pages/Logsx`
    - `frontend/src/pages/Login.tsx`
    - `/src/pagesSetup.tsx`
  - Related Milestones: m3-frontend-session-tests
  - Recommendation: 至少补齐三测试：1) workspace 白名单/越权/下载鉴权测试；2) outbound logs 对成功与失败请求记录测试；3) healthz/readyz态码分离测试。
<!-- LIMCODE_REVIEW_FINDINGS_END -->

## Review Milestones
<!-- LIMCODE_REVIEW_MILESTONES_START -->
### m1-runtime-observability · 审查运行时与可观测性核心链路
- Status: completed
- Recorded At: 2026-03-18T13:40:16.809Z
- Reviewed Modules: main.py, core/http.py, core/log_config.py, core/watchdog.py, routes/health, routes/stats.py
- Summary:
已检查 `main.py`、`core/http.py`、`core/log_config.py`、`core/watchdog.py`、`routes/health.py` 与 `routes/stats.py`。整体上启动时序、日志采集健康检查接线完整，但发现两个关键问题：1) 出站 HTTP 拦截仅在收到响应后写入缓冲区，连接失败/超时类请求不会留下记录，未满足“记录全部出站请求”的目标；2) `/healthz` 与 `/ready` 共享完全相同的判定逻辑，`readiness` 参数未被使用，导致健康探针语义没有真正区分存活与就绪。
- Conclusion: 运行时骨架可用，但当前可观测性在“失败请求追踪”和“探针语义”两个关键点上仍不完整。
- Evidence Files:
  - `main.py`
  - `core/http.py`
  - `core/log_config.py`
  - `core/watchdog.py`
  - `routes/health.py`
  - `routes/stats.py`
- Recommended Next Action: 继续审查文件管理与管理员边界，重点确认 whitelist、凭证传递和前端行为是否符合安全要求。
- Findings:
  - [high] other: 出站 HTTP 拦截不会连接失败/超时类请求
  - [medium] maintainability: healthz 与 readyz 没有真正区分存活和就绪义

### m2-workspace-security · 审查工作区文件管理与管理员边界
- Status: completed
- Recorded At: 2026-03-18T13:41:11.658Z
- Reviewed Modules: routes/workspace.py, frontend/src/pages/Workspace.tsxcore/auth.py, routes/__init__.py
- Summary:
检查 `routes/workspace.py`、`frontend/src/pages/Workspace.tsx`、`core/auth.py` 与相关路由注册。文件管理功能的基本读写链路是通的，但实现与最初的安全边界要求有偏差：后端白名单已经从 `api.yaml`/`data/`/`plugins/` 扩展到 `.env`、`Dockerfile`、`-compose.yml`、`pyproject.toml`、`docs/` 等路径；同时前端下载按钮通过 URL query 拼接 JWT，而后端管理员鉴权并不从 读取 token，导致下载链路既存在凭证泄露风险，又大概率直接 403。
- Conclusion: 工作区功能可用，但目前同时存在边界扩大和凭证传递设计错误，两者都需要在上线前收敛。
- Evidence Files:
  - `routes/workspace.py`
  - `frontend/src/pages/Workspace.tsx`
  - `core/auth.py`
  - `routes/__init__.py`
- Recommended Next Action: 继续审前端整体数据获取与会话处理方式，确认新增 `apiFetch` 是否被统一采用，以及是否存在会话失效处理不一致的问题。
- Findings:
  - [high] accessibility: 工作区白名单超出既定范围并暴露敏感配置文件
  - [medium] javascript: 工作区下载功能通过 URL 暴露 token 且与后端鉴权方式不兼容

### m3-frontend-session-tests · 审前端会话链路与测试覆盖
- Status: completed
- Recorded At: 2026-03-18T13:43:06.832Z
- Reviewed Modules: frontend/src/lib/api.ts, frontend/src/pages/Dashboard.tsx, frontend/src/pages/Logs.tsx, frontend/src/pages/Login.tsxfrontend/src/pages/Setup.tsx, test/, core/test/
- Summary:
检查frontend/lib/api.ts`、`frontend/pages/Dashboard.tsx`、`frontend/src/pages/Logs.tsx`、`frontend/src/pages/Login.tsx`、`frontend/src/pages/Setup.tsx` 以及测试目录命中情况。当前前端已经引入 `api` 统一处理本地鉴权失败后的自动退出，但 Dashboard/Logs 等页面仍直接对 `/v1/*` 使用原生 `fetch`，造成会话失效行为不一致；同时新增的 `workspace`/`_logs`/`outbound_logs`/`healthz`/`readyz` 在 `test/` 与 `core/test/` 中都没有对应覆盖。
- Conclusion: 前端基础体验整体可用，但认证请求链路尚未完全收敛，新增关键也缺回归保护。
- Evidence Files:
  - `frontend/src/lib/api.ts`
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/pages/Logsx`
  - `frontend/src/pages/Login.tsx`
  - `/src/pagesSetup.tsx`
  - `test/`
  - `core/test/`
- Recommended Next Action: 结束审查并汇总总体风险，给出上线前必须修复项与可延后项。
- Findings:
  - [medium] javascript: 管理台仍混用原生 fetch 与 apiFetch，导致 JWT 失效处理不一致
  - [low] test: 新增可观测性与工作区功能缺少自动化覆盖
<!-- LIMCODE_REVIEW_MILESTONES_END -->

<!-- LIMCODE_REVIEW_METADATA_START -->
{
  "formatVersion": 3,
  "reviewRunId": "review-mmw2l8r2-4anw8p",
  "createdAt": "2026-03-18T00:00:00.000Z",
  "finalizedAt": "2026-03-18T13:43:46.393Z",
  "status": "completed",
  "overallDecision": "needs_follow_up",
  "latestConclusion": "已完成对当前工作区核心后端、路由层、前端控制台与新增可观测性/工作区功能的全量审查。代码整体结构清晰，启动链路、日志采集、前端页面与基本鉴权都已联通，但当前仍存在不适合直接忽略的上线风险：出站请求拦截未覆盖失败路径，工作区白名单超出约束并暴敏感文件，功能凭证传递方式错误，前端鉴请求链路也尚未完全收敛。综合判断，当前更适“修复后复审”而非直接视为完全通过。",
  "recommendedNextAction": "优先修复四项上线前问题：1) 补齐 outbound failure logging；2) 收缩 workspace 白名单并移除 `.env` 等敏感路径；3) 重做 workspace 下载鉴权4) 统一 `/1/*` 请求到 apiFetch，然后再补最小回归测试后复审。",
  "reviewedModules": [
    "main.py",
    "core/http.py",
    "core/log_config.py",
    "core/watchdog.py",
    "routes/health",
    "routes/stats.py",
    "routes/workspace.py",
    "frontend/src/pages/Workspace.tsxcore/auth.py",
    "routes/__init__.py",
    "frontend/src/lib/api.ts",
    "frontend/src/pages/Dashboard.tsx",
    "frontend/src/pages/Logs.tsx",
    "frontend/src/pages/Login.tsxfrontend/src/pages/Setup.tsx",
    "test/",
    "core/test/"
  ],
  "milestones": [
    {
      "id": "m1-runtime-observability",
      "title": "审查运行时与可观测性核心链路",
      "summary": "已检查 `main.py`、`core/http.py`、`core/log_config.py`、`core/watchdog.py`、`routes/health.py` 与 `routes/stats.py`。整体上启动时序、日志采集健康检查接线完整，但发现两个关键问题：1) 出站 HTTP 拦截仅在收到响应后写入缓冲区，连接失败/超时类请求不会留下记录，未满足“记录全部出站请求”的目标；2) `/healthz` 与 `/ready` 共享完全相同的判定逻辑，`readiness` 参数未被使用，导致健康探针语义没有真正区分存活与就绪。",
      "status": "completed",
      "conclusion": "运行时骨架可用，但当前可观测性在“失败请求追踪”和“探针语义”两个关键点上仍不完整。",
      "evidenceFiles": [
        "main.py",
        "core/http.py",
        "core/log_config.py",
        "core/watchdog.py",
        "routes/health.py",
        "routes/stats.py"
      ],
      "reviewedModules": [
        "main.py",
        "core/http.py",
        "core/log_config.py",
        "core/watchdog.py",
        "routes/health",
        "routes/stats.py"
      ],
      "recommendedNextAction": "继续审查文件管理与管理员边界，重点确认 whitelist、凭证传递和前端行为是否符合安全要求。",
      "recordedAt": "2026-03-18T13:40:16.809Z",
      "findingIds": [
        "F-001",
        "F-002"
      ]
    },
    {
      "id": "m2-workspace-security",
      "title": "审查工作区文件管理与管理员边界",
      "summary": "检查 `routes/workspace.py`、`frontend/src/pages/Workspace.tsx`、`core/auth.py` 与相关路由注册。文件管理功能的基本读写链路是通的，但实现与最初的安全边界要求有偏差：后端白名单已经从 `api.yaml`/`data/`/`plugins/` 扩展到 `.env`、`Dockerfile`、`-compose.yml`、`pyproject.toml`、`docs/` 等路径；同时前端下载按钮通过 URL query 拼接 JWT，而后端管理员鉴权并不从 读取 token，导致下载链路既存在凭证泄露风险，又大概率直接 403。",
      "status": "completed",
      "conclusion": "工作区功能可用，但目前同时存在边界扩大和凭证传递设计错误，两者都需要在上线前收敛。",
      "evidenceFiles": [
        "routes/workspace.py",
        "frontend/src/pages/Workspace.tsx",
        "core/auth.py",
        "routes/__init__.py"
      ],
      "reviewedModules": [
        "routes/workspace.py",
        "frontend/src/pages/Workspace.tsxcore/auth.py",
        "routes/__init__.py"
      ],
      "recommendedNextAction": "继续审前端整体数据获取与会话处理方式，确认新增 `apiFetch` 是否被统一采用，以及是否存在会话失效处理不一致的问题。",
      "recordedAt": "2026-03-18T13:41:11.658Z",
      "findingIds": [
        "-003",
        "-004"
      ]
    },
    {
      "id": "m3-frontend-session-tests",
      "title": "审前端会话链路与测试覆盖",
      "summary": "检查frontend/lib/api.ts`、`frontend/pages/Dashboard.tsx`、`frontend/src/pages/Logs.tsx`、`frontend/src/pages/Login.tsx`、`frontend/src/pages/Setup.tsx` 以及测试目录命中情况。当前前端已经引入 `api` 统一处理本地鉴权失败后的自动退出，但 Dashboard/Logs 等页面仍直接对 `/v1/*` 使用原生 `fetch`，造成会话失效行为不一致；同时新增的 `workspace`/`_logs`/`outbound_logs`/`healthz`/`readyz` 在 `test/` 与 `core/test/` 中都没有对应覆盖。",
      "status": "completed",
      "conclusion": "前端基础体验整体可用，但认证请求链路尚未完全收敛，新增关键也缺回归保护。",
      "evidenceFiles": [
        "frontend/src/lib/api.ts",
        "frontend/src/pages/Dashboard.tsx",
        "frontend/src/pages/Logsx",
        "frontend/src/pages/Login.tsx",
        "/src/pagesSetup.tsx",
        "test/",
        "core/test/"
      ],
      "reviewedModules": [
        "frontend/src/lib/api.ts",
        "frontend/src/pages/Dashboard.tsx",
        "frontend/src/pages/Logs.tsx",
        "frontend/src/pages/Login.tsxfrontend/src/pages/Setup.tsx",
        "test/",
        "core/test/"
      ],
      "recommendedNextAction": "结束审查并汇总总体风险，给出上线前必须修复项与可延后项。",
      "recordedAt": "2026-03-18T13:43:06.832Z",
      "findingIds": [
        "F-005",
        "F-新增可观测性与工作区功能缺少自动化覆盖"
      ]
    }
  ],
  "findings": [
    {
      "id": "F-001",
      "severity": "high",
      "category": "other",
      "title": "出站 HTTP 拦截不会连接失败/超时类请求",
      "description": "`core/http.py` 只在 `_on_response` 中把请求写入缓冲区，而 `httpx` 的 response hook 仅在成功收到响应后才会触发。像ConnectError`、`ReadTimeout`、TLS 握手失败、DNS 失败等场景虽然是最需要排查的出站故障，但当前实现不会留下任何记录，因此与“捕获全部出站请求”的设计目标不一致。",
      "evidenceFiles": [
        "core/http.py",
        "main.py",
        "core/log_config.py",
        "core/watchdog.py",
        "routes/health.py",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m1-runtime-observability"
      ],
      "recommendation": "在 request hook 中先生成一条 pending 记录，或包装 transport/发送调用，在异常路径也写入失败条目（包含异常类型、目标 host、耗时、状态=transport_error 等）。"
    },
    {
      "id": "F-002",
      "severity": "medium",
      "category": "maintainability",
      "title": "healthz 与 readyz 没有真正区分存活和就绪义",
      "description": "`routes/health.py` 的 `__health_payload` 接 `read` 参数，但内部完全没有使用它，导致 `/healthz` 和 `/readyz` 返回相同的状态码与检查逻辑。这样会让外部针无法区分“进程还活着”与“服务已经准备接流量”，在启动/退化阶段容易产生错误的编排行为。",
      "evidenceFiles": [
        "routes/health.py",
        "main.py",
        "core/http.py",
        "core/log_config.py",
        "core/watchdog.py",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m1-runtime-observability"
      ],
      "recommendation": "明确拆分探针职责：`/healthz` 只反映进程存活与事件循环是否完全失控，`readyz` 再额外检查配置、client_manager、channel_manager、startup_completed 等就绪条件。"
    },
    {
      "id": "-003",
      "severity": "high",
      "category": "accessibility",
      "title": "工作区白名单超出既定范围并暴露敏感配置文件",
      "description": "需求约束明确要求工作区严格限制在 `api.yaml`、`data/`、`plugins/`。但 `routes/workspace.py` 的 `WORKSPACE_RULES` 额外放开了 `.env`、`pyproject.toml`、`docker-compose.yml`、`Dockerfile`、`docs/ 等路径，其中 `.env` 可能包含真实凭证或运行时秘密。即便接口是 admin-only，这依属于安全边界扩大和需求偏离。",
      "evidenceFiles": [
        "routes/workspace.py",
        "frontend/src/pages/Workspace.tsx",
        "core/auth.py",
        "routes/__init__.py"
      ],
      "relatedMilestoneIds": [
        "m2-workspace-security"
      ],
      "recommendation": "将白名单收缩回明确要求的三类路径；如果确有运维需求，改为单独的受控 capability 开关，并对 `.env` 这类秘密文件默认永久禁用。"
    },
    {
      "id": "-004",
      "severity": "medium",
      "category": "javascript",
      "title": "工作区下载功能通过 URL 暴露 token 且与后端鉴权方式不兼容",
      "description": "前端 `Workspacex` 用 `window.open('/v1/workspace/download?...&token=...')` 触发下载，但 `core/auth.py` 的 `_admin_api_key` 只从 `Authorization` 或 `x-api-key` 头里取 token，不读取 query 参数。因此下载功能在当前实现会直接 403；同时把 JWT 拼进 URL 还会进入浏览器历史、反向代理日志和监控系统，造成不必要的凭证暴露。",
      "evidenceFiles": [
        "routes/workspace.py",
        "frontend/src/pages/Workspace.tsx",
        "core/auth.py",
        "routes/__init__.py"
      ],
      "relatedMilestoneIds": [
        "m2-workspace-security"
      ],
      "recommendation": "改为使用带 `Authorization` 头的 `fetch/blob` 下载，或在后端提供一次性短时下载票据，不要把长期 JWT 放进查询串。"
    },
    {
      "id": "F-005",
      "severity": "medium",
      "category": "javascript",
      "title": "管理台仍混用原生 fetch 与 apiFetch，导致 JWT 失效处理不一致",
      "description": "`frontend/src/lib.ts` 已封装本地鉴权失败后的统一 `logout + 跳转登录页` 辑，但 `.tsx`、`Logs.tsx` 等页面仍直接对 `/v1/*`用原生 `fetch`。这会使部分页面在 JWT 失效后继续停留在当前页面、只表现为静默失败或局部报错，而另一些页面会正确到登录页，形成不一致的会话体验。",
      "evidenceFiles": [
        "frontend/src/lib/api.ts",
        "frontend/src/pages/Dashboardx",
        "frontend/src/pages/Logs.tsx",
        "frontend/src/pages/Dashboard.tsx",
        "frontend/src/pages/Logsx",
        "frontend/src/pages/Login.tsx",
        "/src/pagesSetup.tsx",
        "test/",
        "core/test/"
      ],
      "relatedMilestoneIds": [
        "m3-frontend-session-tests"
      ],
      "recommendation": "将需要管理端鉴权的 `/v1/*` 请求统一收敛到 `apiFetch`，并为少数需要特殊处理的页面提供显式 opt-out 注释，而不是继续混用两套请求方式。"
    },
    {
      "id": "F-新增可观测性与工作区功能缺少自动化覆盖",
      "severity": "low",
      "category": "test",
      "title": "新增可观测性与工作区功能缺少自动化覆盖",
      "description": "针对 `workspace`、`backend_logs、`outbound_logs`、`healthz`、`readyz` 的关键路径 `test/` 与 `core/test/` 中均未找到对应测试由于这些功能同时涉及鉴权、文件边界、健康探针和 monkey-patch，缺乏回归测试会后续重构风险明显偏。",
      "evidenceFiles": [
        "test/",
        "core/test/",
        "routesspace.py",
        "routes/stats.py",
        "routes/health.py",
        "core/http.py",
        "frontend/src/lib/api.ts",
        "frontend/src/pages/Dashboard.tsx",
        "frontend/src/pages/Logsx",
        "frontend/src/pages/Login.tsx",
        "/src/pagesSetup.tsx"
      ],
      "relatedMilestoneIds": [
        "m3-frontend-session-tests"
      ],
      "recommendation": "至少补齐三测试：1) workspace 白名单/越权/下载鉴权测试；2) outbound logs 对成功与失败请求记录测试；3) healthz/readyz态码分离测试。"
    }
  ]
}
<!-- LIMCODE_REVIEW_METADATA_END -->
