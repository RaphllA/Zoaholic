# 渠道分析改动评审
- Date: 2026-03-18
- Overview: 审查本次渠道分析侧滑面板与趋势接口改动，重点关注需求覆盖度、数据一致性与前端集成风险。
- Status: completed
- Overall decision: needs_follow_up

## Review Scope
# 渠道分析改动评审

- 日期：2026-03-18
- 范围：`routes/stats.py`、`frontend/src/components/ChannelAnalyticsSheet.tsx`、`frontend/src/pages/Channels.tsx`

### 审查目标
针对本次“渠道分析”改动进行增量评审，重点核对：

1. 现有接口扩展是否保持兼容。
2. 右侧侧滑面板是否覆盖用户提出的核心分析诉求。
3. 面板中的指标是否来自一致的数据口径。
4. 入口接入是否影响渠道配置页原有交互。

### 当前结论
本次改动在工程实现上是通的：后端趋势接口扩展保持兼容，渠道页入口与侧滑面板也已完成接线，前端类型检查通过。但从需求完成度与数据可信度看，当前版本仍需继续跟进。最关键的问题是：用户明确提出的“每个 Key 的次数与 Token 用量”尚未落地；此外，概览卡片把 RequestStat 与 ChannelStat 两套口径混合展示，在存在重试/回退时会给出不对应同一分母的成功率与请求量，容易误导使用者。建议先补齐 Key 维度 token 聚合，并统一或明确区分面板顶部指标口径，再把该分析面板视为完成。

## Review Summary
<!-- LIMCODE_REVIEW_SUMMARY_START -->
- Current status: completed
- Reviewed modules: routes/stats.py, frontend/src/components/ChannelAnalyticsSheet.tsx, frontend/src/pages/Channels.tsx
- Current progress: 2 milestones recorded; latest: m2-frontend-sheet-and-entry
- Total milestones: 2
- Completed milestones: 2
- Total findings: 6
- Findings by severity: high 1 / medium 1 / low 4
- Latest conclusion: 本次改动在工程实现上是通的：后端趋势接口扩展保持兼容，渠道页入口与侧滑面板也已完成接线，前端类型检查通过。但从需求完成度与数据可信度看，当前版本仍需继续跟进。最关键的问题是：用户明确提出的“每个 Key 的次数与 Token 用量”尚未落地；此外，概览卡片把 RequestStat 与 ChannelStat 两套口径混合展示，在存在重试/回退时会给出不对应同一分母的成功率与请求量，容易误导使用者。建议先补齐 Key 维度 token 聚合，并统一或明确区分面板顶部指标口径，再把该分析面板视为完成。
- Recommended next action: 先补齐每个 Key 的 token 用量聚合与展示，再统一概览卡片的数据口径；完成后顺手修正中小屏侧滑宽度约束。
- Overall decision: needs_follow_up
<!-- LIMCODE_REVIEW_SUMMARY_END -->

## Review Findings
<!-- LIMCODE_REVIEW_FINDINGS_START -->
- [low] other: 渠道分析面板尚未实现“每个 Key 的 Token 用量”展示，当前只展示成功率排名，未覆盖本次需求中的核心分析项。
  - ID: F-渠道分析面板尚未实现-每个-key-的-token-用量-展示-当前只展示成功率排名-未覆盖本次需求中的核心分析项
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `frontend/src/pages/Channels.tsx`
    - `routes/stats.py`
  - Related Milestones: m2-frontend-sheet-and-entry

- [low] other: 概览卡片将 RequestStat 与 ChannelStat 混用，导致“总请求量”和“成功率”在有重试时不再对应同一分母，面板会出现口径不一致的结论。
  - ID: F-概览卡片将-requeststat-与-channelstat-混用-导致-总请求量-和-成功率-在有重试时不再对应同一分母-面板会出现口径不一致的结论
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `frontend/src/pages/Channels.tsx`
    - `routes/stats.py`
  - Related Milestones: m2-frontend-sheet-and-entry

- [low] other: 侧滑面板在 `sm` 断点使用固定 720px 宽度，640-719px 设备上会出现横向溢出风险。
  - ID: F-侧滑面板在-sm-断点使用固定-720px-宽度-640-719px-设备上会出现横向溢出风险
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `frontend/src/pages/Channels.tsx`
    - `routes/stats.py`
  - Related Milestones: m2-frontend-sheet-and-entry

- [high] javascript: 每个 Key 的 Token 用量需求未实现
  - ID: F-001
  - Description: 用户需求明确要求渠道分析中展示“每个 key 的用量（次数和 token）”。但当前侧滑面板的 Key 区块仅渲染 `success_count`、`total_requests` 和 `success_rate`，后端也仍然只通过 `/v1/channel_key_rankings` 返回排名数据，没有任何 prompt/completion/total token 字段。因此当前交付并未覆盖本次改动的核心需求点。
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `routes/stats.py`
    - `frontend/src/pages/Channels.tsx`
  - Related Milestones: m2-frontend-sheet-and-entry
  - Recommendation: 复用现有统计链路补齐按 Key 聚合的 token 数据；可以优先扩展 `channel_key_rankings` 的返回结构，或提供一个统一的渠道分析汇总载荷，再在侧滑面板中补上对应列。

- [medium] javascript: 概览卡片混用了两套统计口径
  - ID: F-002
  - Description: 面板中的 `totalRequests` / `totalTokens` 来自 `/v1/stats/usage_analysis`（基于 `request_stats`），而 `successRate` 来自 `/v1/stats` 的 `channel_success_rates`（基于 `channel_stats`）。在存在重试、回退或多 Key 尝试时，`channel_stats` 统计的是尝试次数，`request_stats` 统计的是最终请求记录，两者并不共享同一分母。结果是面板顶部会同时展示一个“请求总量”和一个并不对应该总量的成功率，容易误导使用者。
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `routes/stats.py`
    - `frontend/src/pages/Channels.tsx`
  - Related Milestones: m2-frontend-sheet-and-entry
  - Recommendation: 将概览卡片的核心指标统一到同一数据源；如果需要同时展示“用户请求级”和“上游尝试级”指标，应在 UI 标签中显式区分，例如“请求成功率”与“上游尝试成功率”。

- [low] css: 中小屏宽度下侧滑面板可能横向溢出
  - ID: F-003
  - Description: 侧滑面板使用 `w-full sm:w-[720px]`。在 Tailwind 的 `sm` 断点（>=640px）到 719px 之间，组件会强制使用 720px 固定宽度，超过可视区域宽度时会造成横向溢出或可视裁切。该问题不会影响桌面端，但会影响较窄平板或小尺寸横屏设备上的可用性。
  - Evidence Files:
    - `frontend/src/components/ChannelAnalyticsSheet.tsx`
    - `frontend/src/pages/Channels.tsx`
    - `routes/stats.py`
  - Related Milestones: m2-frontend-sheet-and-entry
  - Recommendation: 改为 `w-full md:w-[720px]`，或保留固定宽度的同时增加 `max-w-[100vw]`/`max-w-full` 约束。
<!-- LIMCODE_REVIEW_FINDINGS_END -->

## Review Milestones
<!-- LIMCODE_REVIEW_MILESTONES_START -->
### m1-backend-model-trend · 后端趋势接口扩展复核
- Status: completed
- Recorded At: 2026-03-18T09:44:40.122Z
- Reviewed Modules: routes/stats.py
- Summary:
已复核 `routes/stats.py` 中 `/v1/stats/model_trend` 的改动。

- 在原有 `data`（按小时、按模型的请求次数序列）之外，新增了 `tokens_data` 返回字段。
- 新字段通过独立的 `tokens_chart_dict` 生成，不会破坏现有 `data` 字段的结构，因此对现有 Dashboard 调用方保持向后兼容。
- 前端若不消费 `tokens_data`，原有行为不受影响；新侧滑面板可以直接复用同一接口切换“请求次数 / Token 消耗”两种趋势视图。

本单元未发现阻塞性问题，接口扩展方式较为克制，复用思路合理。
- Conclusion: 后端接口扩展整体兼容，能够在不新增额外接口的前提下支撑趋势维度切换。
- Evidence Files:
  - `routes/stats.py`
- Recommended Next Action: 继续复核前端侧滑面板是否完整覆盖需求并保持数据口径一致。

### m2-frontend-sheet-and-entry · 前端侧滑面板与渠道页入口复核
- Status: completed
- Recorded At: 2026-03-18T09:45:17.589Z
- Reviewed Modules: frontend/src/components/ChannelAnalyticsSheet.tsx, frontend/src/pages/Channels.tsx
- Summary:
已复核 `frontend/src/components/ChannelAnalyticsSheet.tsx` 与 `frontend/src/pages/Channels.tsx` 的接入方式。

正向结论：

- 渠道页在移动端卡片和桌面端表格中都新增了统一的“分析”入口，接入位置清晰，不会破坏原有编辑/测试/启停按钮的顺序。
- 侧滑面板采用独立组件实现，趋势图、模型明细、Key 健康度和失败日志均通过现有接口复用完成，整体复用思路合理。
- `npx tsc --noEmit` 已通过，说明当前前端改动至少在类型层面没有引入编译错误。

但该单元仍有 3 个需要跟进的问题：一个需求缺口、一个指标口径不一致问题，以及一个中小屏侧滑宽度问题。
- Conclusion: 前端侧滑方案已经能工作，但当前版本仍不能视为完整交付：核心的“每个 Key 的 Token 用量”未落地，且概览指标存在口径混用。
- Evidence Files:
  - `frontend/src/components/ChannelAnalyticsSheet.tsx`
  - `frontend/src/pages/Channels.tsx`
  - `routes/stats.py`
- Recommended Next Action: 优先补齐 Key 维度的 token 聚合，并统一概览卡片的数据口径；随后再调整侧滑面板的中小屏宽度约束。
- Findings:
  - [low] other: 渠道分析面板尚未实现“每个 Key 的 Token 用量”展示，当前只展示成功率排名，未覆盖本次需求中的核心分析项。
  - [low] other: 概览卡片将 RequestStat 与 ChannelStat 混用，导致“总请求量”和“成功率”在有重试时不再对应同一分母，面板会出现口径不一致的结论。
  - [low] other: 侧滑面板在 `sm` 断点使用固定 720px 宽度，640-719px 设备上会出现横向溢出风险。
  - [high] javascript: 每个 Key 的 Token 用量需求未实现
  - [medium] javascript: 概览卡片混用了两套统计口径
  - [low] css: 中小屏宽度下侧滑面板可能横向溢出
<!-- LIMCODE_REVIEW_MILESTONES_END -->

<!-- LIMCODE_REVIEW_METADATA_START -->
{
  "formatVersion": 3,
  "reviewRunId": "review-mmvuu3pu-m71oms",
  "createdAt": "2026-03-18T00:00:00.000Z",
  "finalizedAt": "2026-03-18T09:45:58.340Z",
  "status": "completed",
  "overallDecision": "needs_follow_up",
  "latestConclusion": "本次改动在工程实现上是通的：后端趋势接口扩展保持兼容，渠道页入口与侧滑面板也已完成接线，前端类型检查通过。但从需求完成度与数据可信度看，当前版本仍需继续跟进。最关键的问题是：用户明确提出的“每个 Key 的次数与 Token 用量”尚未落地；此外，概览卡片把 RequestStat 与 ChannelStat 两套口径混合展示，在存在重试/回退时会给出不对应同一分母的成功率与请求量，容易误导使用者。建议先补齐 Key 维度 token 聚合，并统一或明确区分面板顶部指标口径，再把该分析面板视为完成。",
  "recommendedNextAction": "先补齐每个 Key 的 token 用量聚合与展示，再统一概览卡片的数据口径；完成后顺手修正中小屏侧滑宽度约束。",
  "reviewedModules": [
    "routes/stats.py",
    "frontend/src/components/ChannelAnalyticsSheet.tsx",
    "frontend/src/pages/Channels.tsx"
  ],
  "milestones": [
    {
      "id": "m1-backend-model-trend",
      "title": "后端趋势接口扩展复核",
      "summary": "已复核 `routes/stats.py` 中 `/v1/stats/model_trend` 的改动。\n\n- 在原有 `data`（按小时、按模型的请求次数序列）之外，新增了 `tokens_data` 返回字段。\n- 新字段通过独立的 `tokens_chart_dict` 生成，不会破坏现有 `data` 字段的结构，因此对现有 Dashboard 调用方保持向后兼容。\n- 前端若不消费 `tokens_data`，原有行为不受影响；新侧滑面板可以直接复用同一接口切换“请求次数 / Token 消耗”两种趋势视图。\n\n本单元未发现阻塞性问题，接口扩展方式较为克制，复用思路合理。",
      "status": "completed",
      "conclusion": "后端接口扩展整体兼容，能够在不新增额外接口的前提下支撑趋势维度切换。",
      "evidenceFiles": [
        "routes/stats.py"
      ],
      "reviewedModules": [
        "routes/stats.py"
      ],
      "recommendedNextAction": "继续复核前端侧滑面板是否完整覆盖需求并保持数据口径一致。",
      "recordedAt": "2026-03-18T09:44:40.122Z",
      "findingIds": []
    },
    {
      "id": "m2-frontend-sheet-and-entry",
      "title": "前端侧滑面板与渠道页入口复核",
      "summary": "已复核 `frontend/src/components/ChannelAnalyticsSheet.tsx` 与 `frontend/src/pages/Channels.tsx` 的接入方式。\n\n正向结论：\n\n- 渠道页在移动端卡片和桌面端表格中都新增了统一的“分析”入口，接入位置清晰，不会破坏原有编辑/测试/启停按钮的顺序。\n- 侧滑面板采用独立组件实现，趋势图、模型明细、Key 健康度和失败日志均通过现有接口复用完成，整体复用思路合理。\n- `npx tsc --noEmit` 已通过，说明当前前端改动至少在类型层面没有引入编译错误。\n\n但该单元仍有 3 个需要跟进的问题：一个需求缺口、一个指标口径不一致问题，以及一个中小屏侧滑宽度问题。",
      "status": "completed",
      "conclusion": "前端侧滑方案已经能工作，但当前版本仍不能视为完整交付：核心的“每个 Key 的 Token 用量”未落地，且概览指标存在口径混用。",
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx",
        "routes/stats.py"
      ],
      "reviewedModules": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx"
      ],
      "recommendedNextAction": "优先补齐 Key 维度的 token 聚合，并统一概览卡片的数据口径；随后再调整侧滑面板的中小屏宽度约束。",
      "recordedAt": "2026-03-18T09:45:17.589Z",
      "findingIds": [
        "F-渠道分析面板尚未实现-每个-key-的-token-用量-展示-当前只展示成功率排名-未覆盖本次需求中的核心分析项",
        "F-概览卡片将-requeststat-与-channelstat-混用-导致-总请求量-和-成功率-在有重试时不再对应同一分母-面板会出现口径不一致的结论",
        "F-侧滑面板在-sm-断点使用固定-720px-宽度-640-719px-设备上会出现横向溢出风险",
        "F-001",
        "F-002",
        "F-003"
      ]
    }
  ],
  "findings": [
    {
      "id": "F-渠道分析面板尚未实现-每个-key-的-token-用量-展示-当前只展示成功率排名-未覆盖本次需求中的核心分析项",
      "severity": "low",
      "category": "other",
      "title": "渠道分析面板尚未实现“每个 Key 的 Token 用量”展示，当前只展示成功率排名，未覆盖本次需求中的核心分析项。",
      "description": null,
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": null
    },
    {
      "id": "F-概览卡片将-requeststat-与-channelstat-混用-导致-总请求量-和-成功率-在有重试时不再对应同一分母-面板会出现口径不一致的结论",
      "severity": "low",
      "category": "other",
      "title": "概览卡片将 RequestStat 与 ChannelStat 混用，导致“总请求量”和“成功率”在有重试时不再对应同一分母，面板会出现口径不一致的结论。",
      "description": null,
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": null
    },
    {
      "id": "F-侧滑面板在-sm-断点使用固定-720px-宽度-640-719px-设备上会出现横向溢出风险",
      "severity": "low",
      "category": "other",
      "title": "侧滑面板在 `sm` 断点使用固定 720px 宽度，640-719px 设备上会出现横向溢出风险。",
      "description": null,
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": null
    },
    {
      "id": "F-001",
      "severity": "high",
      "category": "javascript",
      "title": "每个 Key 的 Token 用量需求未实现",
      "description": "用户需求明确要求渠道分析中展示“每个 key 的用量（次数和 token）”。但当前侧滑面板的 Key 区块仅渲染 `success_count`、`total_requests` 和 `success_rate`，后端也仍然只通过 `/v1/channel_key_rankings` 返回排名数据，没有任何 prompt/completion/total token 字段。因此当前交付并未覆盖本次改动的核心需求点。",
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "routes/stats.py",
        "frontend/src/pages/Channels.tsx"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": "复用现有统计链路补齐按 Key 聚合的 token 数据；可以优先扩展 `channel_key_rankings` 的返回结构，或提供一个统一的渠道分析汇总载荷，再在侧滑面板中补上对应列。"
    },
    {
      "id": "F-002",
      "severity": "medium",
      "category": "javascript",
      "title": "概览卡片混用了两套统计口径",
      "description": "面板中的 `totalRequests` / `totalTokens` 来自 `/v1/stats/usage_analysis`（基于 `request_stats`），而 `successRate` 来自 `/v1/stats` 的 `channel_success_rates`（基于 `channel_stats`）。在存在重试、回退或多 Key 尝试时，`channel_stats` 统计的是尝试次数，`request_stats` 统计的是最终请求记录，两者并不共享同一分母。结果是面板顶部会同时展示一个“请求总量”和一个并不对应该总量的成功率，容易误导使用者。",
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "routes/stats.py",
        "frontend/src/pages/Channels.tsx"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": "将概览卡片的核心指标统一到同一数据源；如果需要同时展示“用户请求级”和“上游尝试级”指标，应在 UI 标签中显式区分，例如“请求成功率”与“上游尝试成功率”。"
    },
    {
      "id": "F-003",
      "severity": "low",
      "category": "css",
      "title": "中小屏宽度下侧滑面板可能横向溢出",
      "description": "侧滑面板使用 `w-full sm:w-[720px]`。在 Tailwind 的 `sm` 断点（>=640px）到 719px 之间，组件会强制使用 720px 固定宽度，超过可视区域宽度时会造成横向溢出或可视裁切。该问题不会影响桌面端，但会影响较窄平板或小尺寸横屏设备上的可用性。",
      "evidenceFiles": [
        "frontend/src/components/ChannelAnalyticsSheet.tsx",
        "frontend/src/pages/Channels.tsx",
        "routes/stats.py"
      ],
      "relatedMilestoneIds": [
        "m2-frontend-sheet-and-entry"
      ],
      "recommendation": "改为 `w-full md:w-[720px]`，或保留固定宽度的同时增加 `max-w-[100vw]`/`max-w-full` 约束。"
    }
  ]
}
<!-- LIMCODE_REVIEW_METADATA_END -->
