# all-uncommitted-code-review
- Date: 2026-03-19
- Overview: 审查当前工作区全部未提交业务代码与测试改动，覆盖透传机制、方言路由、Responses 解析与测试一致性。
- Status: completed
- Overall decision: needs_follow_up

## Review Scope
# 全量未提交代码评审

- 日期：2026-03-19
- 范围：当前工作区全部未提交代码（不含本次新建 review 文档本身）
- 目标：识别未提交改动的实现风险、兼容性问题与测试覆盖偏差

1. 获取 git 未提交文件与 diff 摘要
2. 按核心模块审查业务代码改动
3. 审查测试改动与行为一致性
4. 汇总是否建议合并

## Review Summary
<!-- LIMCODE_REVIEW_SUMMARY_START -->
- Current status: completed
- Reviewed modules: core/dialects/registry.py, core/dialects/router.py, core/handler.py, core/dialects/claude.py, core/dialects/openai_responses.py, test/dialects/test_dialects.py, core/channels/openai_channel.py
- Current progress: 2 milestones recorded; latest: m2
- Total milestones: 2
- Completed milestones: 2
- Total findings: 2
- Findings by severity: high 1 / medium 0 / low 1
- Latest conclusion: 当前未提交改动在结构上比早期方案更成熟：透传支持已经从针对单一子端点的补丁式实现，演进为显式的 `passthrough_root` + `passthrough_only` 机制；Responses 解析也补上了顶层 `instructions` 到 system message 的映射，测试职责边界总体更清晰。但仍不建议直接合并，主要原因是高风险问题仍存在：`passthrough_only` 的不兼容判定虽然前移到了请求发送前，却仍然进入通用 provider 故障处理路径，从而可能触发渠道冷却、API key cooling 和重试惩罚，错误污染后续正常请求的 provider 可用性状态。除此之外，Responses 新增 `instructions` 语义尚缺少直接回归测试。建议先把“协议不兼容的本地跳过”与“真实 provider 故障”彻底分离，再补足 `instructions` 的显式测试后合并。
- Recommended next action: 优先将 `passthrough_only` 的不兼容处理改为本地 skip 语义（而非 HTTPException 进入统一故障路径），确保不触发 channel cooldown、key cooling 与故障统计；随后补一个直接验证顶层 `instructions` 映射的测试用例。
- Overall decision: needs_follow_up
<!-- LIMCODE_REVIEW_SUMMARY_END -->

## Review Findings
<!-- LIMCODE_REVIEW_FINDINGS_START -->
- [high] other: `passthrough_only` 的本地兼容性拒绝仍会触发渠道冷却与 key cooling
  - ID: F-101
  - Description: 在 `ModelRequestHandler.request_model()` 中，`passthrough_only` 不兼容 provider 会在发送请求前抛出 `HTTPException(501)`，这解决了误发上游请求的问题；但该异常随后仍进入统一的错误处理分支。根据 `core/handler.py` 中的逻辑，它仍可能触发 `channel_manager.exclude_model()`、重算 provider 列表以及 `provider_api_circular_list.set_cooling()`。这会把一次纯本地的“协议不兼容”判定当作 provider 故障，污染后续普通请求的路由与可用性状态。
  - Evidence Files:
    - `core/handler.py`
    - `core/dialects/router.py`
    - `core/dialects/registry.py`
    - `core/dialects/claude.py`
  - Related Milestones: m1
  - Recommendation: 将 `passthrough_only` 的不兼容结果从通用故障路径中分离出来：例如引入专门的本地跳过异常/返回值，使其仅用于跳过当前 provider，不触发渠道冷却、key cooling、故障统计或重试惩罚。

- [low] test: 顶层 `instructions` 新行为已实现但未被测试直接覆盖
  - ID: F-102
  - Description: `parse_responses_request()` 新增了 `instructions -> system message` 映射，但修订后的 `test_openai_responses_parse_input_file` 仍通过 `input` 中的 system message 构造 system 上下文，只间接覆盖了消息顺序而未直接断言顶层 `instructions` 的映射结果。后续若该逻辑回退或被重构破坏，现有测试不一定能及时发现。
  - Evidence Files:
    - `core/dialects/openai_responses.py`
    - `test/dialects/test_dialects.py`
    - `core/channels/openai_channel.py`
  - Related Milestones: m2
  - Recommendation: 补一个显式用例：保留 `input_file` 校验的同时，直接传入顶层 `instructions` 并断言其被转换为首条 system message，以覆盖本次新增语义。
<!-- LIMCODE_REVIEW_FINDINGS_END -->

## Review Milestones
<!-- LIMCODE_REVIEW_MILESTONES_START -->
### m1 · 审查透传根路由与 `passthrough_only` 当前实现
- Status: completed
- Recorded At: 2026-03-19T06:00:04.164Z
- Reviewed Modules: core/dialects/registry.py, core/dialects/router.py, core/handler.py, core/dialects/claude.py
- Summary:
已审查 `core/dialects/registry.py`、`core/dialects/router.py`、`core/handler.py`、`core/dialects/claude.py` 当前未提交改动。

正面结论：
- 设计已经从“单子端点补丁”推进到“按资源根透传”，`EndpointDefinition.passthrough_root` 比早先基于字面路径前缀推导更清晰、更可扩展。
- `passthrough_only` 的兼容性判定已前移到请求发送前，避免了对不兼容上游发出真实请求，这一方向是正确的。

剩余问题：
- 当前对“不兼容 provider”的处理方式仍然是抛出 `HTTPException(501)` 进入通用错误路径。这样虽然不再请求上游，但仍会进入统一的重试、渠道冷却和 API key cooling 逻辑，导致一个纯本地的“协议不兼容”判定被当作 provider 故障处理，可能污染后续正常流量的 provider 可用性判断。
- Conclusion: 核心透传结构比之前合理，但协议不兼容仍被错误地纳入 provider 故障治理路径，风险较高。
- Evidence Files:
  - `core/dialects/registry.py`
  - `core/dialects/router.py`
  - `core/handler.py`
  - `core/dialects/claude.py`
- Recommended Next Action: 继续审查 Responses 解析与测试文件，确认本次未提交改动是否完整覆盖新引入语义。
- Findings:
  - [high] other: `passthrough_only` 的本地兼容性拒绝仍会触发渠道冷却与 key cooling

### m2 · 审查 Responses 解析与测试改动一致性
- Status: completed
- Recorded At: 2026-03-19T06:00:47.173Z
- Reviewed Modules: core/dialects/openai_responses.py, test/dialects/test_dialects.py, core/channels/openai_channel.py
- Summary:
已审查 `core/dialects/openai_responses.py`、`test/dialects/test_dialects.py`、`core/channels/openai_channel.py` 当前未提交改动。

正面结论：
- `parse_responses_request()` 现已显式处理顶层 `instructions -> system message`，与公开 Responses API 语义更一致。
- `test_apply_passthrough_system_prompt_openai` 已改为验证渠道级 `patch_passthrough_openai_payload()`，职责边界比旧测试更准确。

剩余问题：
- 新增的 `instructions` 映射行为当前没有被测试直接覆盖。现有 `test_openai_responses_parse_input_file` 主要验证 `input_file` 转换，system 内容则来自 `input` 中的 system message，而不是顶层 `instructions`。因此，本次代码虽然实现了 `instructions` 支持，但对应行为仍缺少回归保护。
- Conclusion: Responses 解析方向正确，但本次新增语义的测试覆盖仍不完整。
- Evidence Files:
  - `core/dialects/openai_responses.py`
  - `test/dialects/test_dialects.py`
  - `core/channels/openai_channel.py`
- Recommended Next Action: 汇总当前未提交代码的剩余风险并给出最终合并建议。
- Findings:
  - [low] test: 顶层 `instructions` 新行为已实现但未被测试直接覆盖
<!-- LIMCODE_REVIEW_MILESTONES_END -->

<!-- LIMCODE_REVIEW_METADATA_START -->
{
  "formatVersion": 3,
  "reviewRunId": "review-mmx23hci-dg30m1",
  "createdAt": "2026-03-19T00:00:00.000Z",
  "finalizedAt": "2026-03-19T06:01:14.170Z",
  "status": "completed",
  "overallDecision": "needs_follow_up",
  "latestConclusion": "当前未提交改动在结构上比早期方案更成熟：透传支持已经从针对单一子端点的补丁式实现，演进为显式的 `passthrough_root` + `passthrough_only` 机制；Responses 解析也补上了顶层 `instructions` 到 system message 的映射，测试职责边界总体更清晰。但仍不建议直接合并，主要原因是高风险问题仍存在：`passthrough_only` 的不兼容判定虽然前移到了请求发送前，却仍然进入通用 provider 故障处理路径，从而可能触发渠道冷却、API key cooling 和重试惩罚，错误污染后续正常请求的 provider 可用性状态。除此之外，Responses 新增 `instructions` 语义尚缺少直接回归测试。建议先把“协议不兼容的本地跳过”与“真实 provider 故障”彻底分离，再补足 `instructions` 的显式测试后合并。",
  "recommendedNextAction": "优先将 `passthrough_only` 的不兼容处理改为本地 skip 语义（而非 HTTPException 进入统一故障路径），确保不触发 channel cooldown、key cooling 与故障统计；随后补一个直接验证顶层 `instructions` 映射的测试用例。",
  "reviewedModules": [
    "core/dialects/registry.py",
    "core/dialects/router.py",
    "core/handler.py",
    "core/dialects/claude.py",
    "core/dialects/openai_responses.py",
    "test/dialects/test_dialects.py",
    "core/channels/openai_channel.py"
  ],
  "milestones": [
    {
      "id": "m1",
      "title": "审查透传根路由与 `passthrough_only` 当前实现",
      "summary": "已审查 `core/dialects/registry.py`、`core/dialects/router.py`、`core/handler.py`、`core/dialects/claude.py` 当前未提交改动。\n\n正面结论：\n- 设计已经从“单子端点补丁”推进到“按资源根透传”，`EndpointDefinition.passthrough_root` 比早先基于字面路径前缀推导更清晰、更可扩展。\n- `passthrough_only` 的兼容性判定已前移到请求发送前，避免了对不兼容上游发出真实请求，这一方向是正确的。\n\n剩余问题：\n- 当前对“不兼容 provider”的处理方式仍然是抛出 `HTTPException(501)` 进入通用错误路径。这样虽然不再请求上游，但仍会进入统一的重试、渠道冷却和 API key cooling 逻辑，导致一个纯本地的“协议不兼容”判定被当作 provider 故障处理，可能污染后续正常流量的 provider 可用性判断。",
      "status": "completed",
      "conclusion": "核心透传结构比之前合理，但协议不兼容仍被错误地纳入 provider 故障治理路径，风险较高。",
      "evidenceFiles": [
        "core/dialects/registry.py",
        "core/dialects/router.py",
        "core/handler.py",
        "core/dialects/claude.py"
      ],
      "reviewedModules": [
        "core/dialects/registry.py",
        "core/dialects/router.py",
        "core/handler.py",
        "core/dialects/claude.py"
      ],
      "recommendedNextAction": "继续审查 Responses 解析与测试文件，确认本次未提交改动是否完整覆盖新引入语义。",
      "recordedAt": "2026-03-19T06:00:04.164Z",
      "findingIds": [
        "F-101"
      ]
    },
    {
      "id": "m2",
      "title": "审查 Responses 解析与测试改动一致性",
      "summary": "已审查 `core/dialects/openai_responses.py`、`test/dialects/test_dialects.py`、`core/channels/openai_channel.py` 当前未提交改动。\n\n正面结论：\n- `parse_responses_request()` 现已显式处理顶层 `instructions -> system message`，与公开 Responses API 语义更一致。\n- `test_apply_passthrough_system_prompt_openai` 已改为验证渠道级 `patch_passthrough_openai_payload()`，职责边界比旧测试更准确。\n\n剩余问题：\n- 新增的 `instructions` 映射行为当前没有被测试直接覆盖。现有 `test_openai_responses_parse_input_file` 主要验证 `input_file` 转换，system 内容则来自 `input` 中的 system message，而不是顶层 `instructions`。因此，本次代码虽然实现了 `instructions` 支持，但对应行为仍缺少回归保护。",
      "status": "completed",
      "conclusion": "Responses 解析方向正确，但本次新增语义的测试覆盖仍不完整。",
      "evidenceFiles": [
        "core/dialects/openai_responses.py",
        "test/dialects/test_dialects.py",
        "core/channels/openai_channel.py"
      ],
      "reviewedModules": [
        "core/dialects/openai_responses.py",
        "test/dialects/test_dialects.py",
        "core/channels/openai_channel.py"
      ],
      "recommendedNextAction": "汇总当前未提交代码的剩余风险并给出最终合并建议。",
      "recordedAt": "2026-03-19T06:00:47.173Z",
      "findingIds": [
        "F-102"
      ]
    }
  ],
  "findings": [
    {
      "id": "F-101",
      "severity": "high",
      "category": "other",
      "title": "`passthrough_only` 的本地兼容性拒绝仍会触发渠道冷却与 key cooling",
      "description": "在 `ModelRequestHandler.request_model()` 中，`passthrough_only` 不兼容 provider 会在发送请求前抛出 `HTTPException(501)`，这解决了误发上游请求的问题；但该异常随后仍进入统一的错误处理分支。根据 `core/handler.py` 中的逻辑，它仍可能触发 `channel_manager.exclude_model()`、重算 provider 列表以及 `provider_api_circular_list.set_cooling()`。这会把一次纯本地的“协议不兼容”判定当作 provider 故障，污染后续普通请求的路由与可用性状态。",
      "evidenceFiles": [
        "core/handler.py",
        "core/dialects/router.py",
        "core/dialects/registry.py",
        "core/dialects/claude.py"
      ],
      "relatedMilestoneIds": [
        "m1"
      ],
      "recommendation": "将 `passthrough_only` 的不兼容结果从通用故障路径中分离出来：例如引入专门的本地跳过异常/返回值，使其仅用于跳过当前 provider，不触发渠道冷却、key cooling、故障统计或重试惩罚。"
    },
    {
      "id": "F-102",
      "severity": "low",
      "category": "test",
      "title": "顶层 `instructions` 新行为已实现但未被测试直接覆盖",
      "description": "`parse_responses_request()` 新增了 `instructions -> system message` 映射，但修订后的 `test_openai_responses_parse_input_file` 仍通过 `input` 中的 system message 构造 system 上下文，只间接覆盖了消息顺序而未直接断言顶层 `instructions` 的映射结果。后续若该逻辑回退或被重构破坏，现有测试不一定能及时发现。",
      "evidenceFiles": [
        "core/dialects/openai_responses.py",
        "test/dialects/test_dialects.py",
        "core/channels/openai_channel.py"
      ],
      "relatedMilestoneIds": [
        "m2"
      ],
      "recommendation": "补一个显式用例：保留 `input_file` 校验的同时，直接传入顶层 `instructions` 并断言其被转换为首条 system message，以覆盖本次新增语义。"
    }
  ]
}
<!-- LIMCODE_REVIEW_METADATA_END -->
