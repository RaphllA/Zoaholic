# uncommitted-code-review
- Date: 2026-03-19
- Overview: 审查当前工作区全部未提交代码变更，重点关注透传机制、方言路由与测试调整的正确性和可扩展性。
- Status: completed
- Overall decision: needs_follow_up

## Review Scope
# 未提交代码评审

- 日期：2026-03-19
- 范围：当前工作区全部未提交代码
- 目标：检查未提交改动的正确性、兼容性、可维护性与测试一致性

本次评审按以下模块分阶段进行：
1. 识别未提交文件与变更范围
2. 评审透传/方言路由相关核心代码
3. 评审测试变更与行为一致性
4. 汇总结论与风险建议

## Review Summary
<!-- LIMCODE_REVIEW_SUMMARY_START -->
- Current status: completed
- Reviewed modules: core/dialects/registry.py, core/dialects/router.py, core/handler.py, core/dialects/claude.py, test/dialects/test_dialects.py, core/dialects/openai_responses.py, core/channels/openai_channel.py
- Current progress: 2 milestones recorded; latest: m2
- Total milestones: 2
- Completed milestones: 2
- Total findings: 3
- Findings by severity: high 1 / medium 2 / low 0
- Latest conclusion: 本次未提交改动在设计方向上有明显进步：把 Claude 子端点支持从“按单接口补丁”转向了“按资源族透传”，并且测试中对 OpenAI 透传 system_prompt 职责边界的修正是合理的。但当前实现仍不建议直接合并，主要原因有三点：1）`passthrough_only` 的限制生效过晚，非透传 provider 可能已被真实调用，存在潜在计费和副作用风险；2）子路径后缀解析依赖字面路径前缀匹配，尚不足以支撑参数化主路径的通用扩展；3）Responses 相关测试通过收窄输入形态绕开了 `instructions` 未实现问题，掩盖了公开接口兼容性缺口。建议先修复高风险的透传前置拦截问题，并明确/补齐 `passthrough_root` 与 `instructions` 的设计后再合并。
- Recommended next action: 优先前移 `passthrough_only` 的 provider 过滤/拒绝逻辑，避免先请求上游再返回 501；随后将子路径拼接抽象为结构化的 passthrough root 配置，并决定是实现还是显式声明 Responses `instructions` 的支持边界。
- Overall decision: needs_follow_up
<!-- LIMCODE_REVIEW_SUMMARY_END -->

## Review Findings
<!-- LIMCODE_REVIEW_FINDINGS_START -->
- [high] other: `passthrough_only` 在上游请求发送后才拒绝，可能触发错误的真实上游调用
  - ID: F-001
  - Description: `core/dialects/router.py` 仅在 `model_handler.request_model()` 返回响应后才检查 `endpoint.passthrough_only`。而 `ModelRequestHandler.request_model()` 在 provider 与入口方言不匹配时会走普通 `process_request()`，因此像 `/v1/messages/count_tokens` 这样的仅透传端点，仍可能先向非 Claude provider 发送一次真实请求，最后才对客户端返回 501。该顺序会导致无意义的上游调用、潜在计费以及副作用。
  - Evidence Files:
    - `core/dialects/router.py`
    - `core/handler.py`
    - `core/dialects/claude.py`
    - `core/dialects/registry.py`
  - Related Milestones: m1
  - Recommendation: 将 `passthrough_only` 的约束前移到 provider 选择或请求分发之前：要么在路由层提前判定仅允许透传兼容 provider，要么在 `request_model()` 内对这类端点直接跳过非透传 provider，确保不会先发请求后拒绝。

- [medium] maintainability: 透传子路径后缀解析依赖字面路径前缀匹配，无法自然扩展到参数化主路径
  - ID: F-002
  - Description: `core/handler.py` 通过 `endpoint.startswith(_ep.full_path)` 为当前子路径寻找基准主端点，再计算 URL 后缀。该算法只对静态主路径稳定成立；如果未来把同一机制复用于包含路径参数的主端点（例如 `/v1/models/{model}:...` 这类形式），字面字符串前缀将无法匹配真实请求路径，导致后缀解析失效。当前方案对 Claude 可用，但其“通用透传根”抽象仍不完整。
  - Evidence Files:
    - `core/handler.py`
    - `core/dialects/registry.py`
    - `core/dialects/router.py`
    - `core/dialects/claude.py`
  - Related Milestones: m1
  - Recommendation: 不要从 `EndpointDefinition.full_path` 的字面字符串反推主路径。建议显式引入 `passthrough_root`/`base_passthrough_path` 元数据，或为透传根单独建模，使子路径拼接基于结构化配置而不是路由模板字符串。

- [medium] test: Responses 解析测试通过收窄输入形态绕开了 `instructions` 未实现问题
  - ID: F-003
  - Description: 修订后的 `test_openai_responses_parse_input_file` 不再验证顶层 `instructions`，而是把 system 内容塞进 `input` 列表中的 system message。与此同时，`parse_responses_request()` 仍只读取 `model`、`input`、`stream` 等字段，没有把 Responses API 常见的顶层 `instructions` 映射为 Canonical system message。结果是测试现在能通过，但真实接口缺口被隐藏了。
  - Evidence Files:
    - `test/dialects/test_dialects.py`
    - `core/dialects/openai_responses.py`
    - `core/channels/openai_channel.py`
  - Related Milestones: m2
  - Recommendation: 如果产品目标是兼容 Responses API 公开语义，应实现 `instructions -> system message` 的映射；如果暂不支持，则至少保留一个显式测试/文档说明该限制，而不要仅通过改写测试输入形态绕开它。
<!-- LIMCODE_REVIEW_FINDINGS_END -->

## Review Milestones
<!-- LIMCODE_REVIEW_MILESTONES_START -->
### m1 · 审查透传路由与子路径 URL 修正机制
- Status: completed
- Recorded At: 2026-03-19T02:38:54.769Z
- Reviewed Modules: core/dialects/registry.py, core/dialects/router.py, core/handler.py, core/dialects/claude.py
- Summary:
已审查 `core/dialects/registry.py`、`core/dialects/router.py`、`core/handler.py`、`core/dialects/claude.py` 中围绕 `passthrough_only`、Claude 子路径通配路由以及透传 URL 后缀拼接的改动。

结论：方向上从“单个子端点补丁”转向“按资源族透传”是合理的，`/v1/messages/{subpath:path}` + 透传层自动补后缀的设计明显优于为每个子端点单独写 handler。

但当前实现存在两个重要问题：
1. `passthrough_only` 的拒绝发生在上游请求返回之后，而不是 provider 选择或请求发送之前。对于非透传 provider，系统仍会实际发起一次普通转换请求，随后才向客户端返回 501，这会带来错误上游调用与潜在计费风险。
2. 子路径后缀解析依赖于方言 `full_path` 的原始字符串前缀匹配，只适用于静态主路径（如 Claude `/v1/messages`），对带 FastAPI 路径参数的主路径并不通用，扩展到其它协议时可复用性有限。
- Conclusion: 核心设计方向正确，但当前透传保护边界与通用性仍不足，需在后续修正前谨慎合并。
- Evidence Files:
  - `core/dialects/registry.py`
  - `core/dialects/router.py`
  - `core/handler.py`
  - `core/dialects/claude.py`
- Recommended Next Action: 继续审查测试文件改动，重点检查是否存在通过收窄断言来掩盖真实功能缺口的情况。
- Findings:
  - [high] other: `passthrough_only` 在上游请求发送后才拒绝，可能触发错误的真实上游调用
  - [medium] maintainability: 透传子路径后缀解析依赖字面路径前缀匹配，无法自然扩展到参数化主路径

### m2 · 审查测试修订与 Responses 解析行为一致性
- Status: completed
- Recorded At: 2026-03-19T02:40:10.485Z
- Reviewed Modules: test/dialects/test_dialects.py, core/dialects/openai_responses.py, core/channels/openai_channel.py
- Summary:
已审查 `test/dialects/test_dialects.py`、`core/dialects/openai_responses.py`、`core/channels/openai_channel.py`。

结论分两部分：
1. `test_apply_passthrough_system_prompt_openai` 的修订方向是正确的。`system_prompt` 注入本来就是渠道级 `passthrough_payload_adapter` 的职责，而不是 `apply_passthrough_modifications()` 的职责，测试改为直接验证 `patch_passthrough_openai_payload()` 更符合真实实现边界。
2. `test_openai_responses_parse_input_file` 虽然修正了错误的函数名与输入字段名，但它通过把 system 指令改写为 `input` 内的 system message 来回避 `parse_responses_request()` 当前不处理顶层 `instructions` 的事实，从而使测试通过的同时收窄了对公开接口语义的覆盖范围。
- Conclusion: 测试中既有职责对齐的正向修订，也存在为了通过而绕开真实接口缺口的情况；后者应补足产品实现或至少保留显式覆盖。
- Evidence Files:
  - `test/dialects/test_dialects.py`
  - `core/dialects/openai_responses.py`
  - `core/channels/openai_channel.py`
- Recommended Next Action: 汇总全部未提交改动的风险结论，并给出是否建议合并的最终判断。
- Findings:
  - [medium] test: Responses 解析测试通过收窄输入形态绕开了 `instructions` 未实现问题
<!-- LIMCODE_REVIEW_MILESTONES_END -->

<!-- LIMCODE_REVIEW_METADATA_START -->
{
  "formatVersion": 3,
  "reviewRunId": "review-mmwux4hm-66u9ac",
  "createdAt": "2026-03-19T00:00:00.000Z",
  "finalizedAt": "2026-03-19T02:40:39.030Z",
  "status": "completed",
  "overallDecision": "needs_follow_up",
  "latestConclusion": "本次未提交改动在设计方向上有明显进步：把 Claude 子端点支持从“按单接口补丁”转向了“按资源族透传”，并且测试中对 OpenAI 透传 system_prompt 职责边界的修正是合理的。但当前实现仍不建议直接合并，主要原因有三点：1）`passthrough_only` 的限制生效过晚，非透传 provider 可能已被真实调用，存在潜在计费和副作用风险；2）子路径后缀解析依赖字面路径前缀匹配，尚不足以支撑参数化主路径的通用扩展；3）Responses 相关测试通过收窄输入形态绕开了 `instructions` 未实现问题，掩盖了公开接口兼容性缺口。建议先修复高风险的透传前置拦截问题，并明确/补齐 `passthrough_root` 与 `instructions` 的设计后再合并。",
  "recommendedNextAction": "优先前移 `passthrough_only` 的 provider 过滤/拒绝逻辑，避免先请求上游再返回 501；随后将子路径拼接抽象为结构化的 passthrough root 配置，并决定是实现还是显式声明 Responses `instructions` 的支持边界。",
  "reviewedModules": [
    "core/dialects/registry.py",
    "core/dialects/router.py",
    "core/handler.py",
    "core/dialects/claude.py",
    "test/dialects/test_dialects.py",
    "core/dialects/openai_responses.py",
    "core/channels/openai_channel.py"
  ],
  "milestones": [
    {
      "id": "m1",
      "title": "审查透传路由与子路径 URL 修正机制",
      "summary": "已审查 `core/dialects/registry.py`、`core/dialects/router.py`、`core/handler.py`、`core/dialects/claude.py` 中围绕 `passthrough_only`、Claude 子路径通配路由以及透传 URL 后缀拼接的改动。\n\n结论：方向上从“单个子端点补丁”转向“按资源族透传”是合理的，`/v1/messages/{subpath:path}` + 透传层自动补后缀的设计明显优于为每个子端点单独写 handler。\n\n但当前实现存在两个重要问题：\n1. `passthrough_only` 的拒绝发生在上游请求返回之后，而不是 provider 选择或请求发送之前。对于非透传 provider，系统仍会实际发起一次普通转换请求，随后才向客户端返回 501，这会带来错误上游调用与潜在计费风险。\n2. 子路径后缀解析依赖于方言 `full_path` 的原始字符串前缀匹配，只适用于静态主路径（如 Claude `/v1/messages`），对带 FastAPI 路径参数的主路径并不通用，扩展到其它协议时可复用性有限。",
      "status": "completed",
      "conclusion": "核心设计方向正确，但当前透传保护边界与通用性仍不足，需在后续修正前谨慎合并。",
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
      "recommendedNextAction": "继续审查测试文件改动，重点检查是否存在通过收窄断言来掩盖真实功能缺口的情况。",
      "recordedAt": "2026-03-19T02:38:54.769Z",
      "findingIds": [
        "F-001",
        "F-002"
      ]
    },
    {
      "id": "m2",
      "title": "审查测试修订与 Responses 解析行为一致性",
      "summary": "已审查 `test/dialects/test_dialects.py`、`core/dialects/openai_responses.py`、`core/channels/openai_channel.py`。\n\n结论分两部分：\n1. `test_apply_passthrough_system_prompt_openai` 的修订方向是正确的。`system_prompt` 注入本来就是渠道级 `passthrough_payload_adapter` 的职责，而不是 `apply_passthrough_modifications()` 的职责，测试改为直接验证 `patch_passthrough_openai_payload()` 更符合真实实现边界。\n2. `test_openai_responses_parse_input_file` 虽然修正了错误的函数名与输入字段名，但它通过把 system 指令改写为 `input` 内的 system message 来回避 `parse_responses_request()` 当前不处理顶层 `instructions` 的事实，从而使测试通过的同时收窄了对公开接口语义的覆盖范围。",
      "status": "completed",
      "conclusion": "测试中既有职责对齐的正向修订，也存在为了通过而绕开真实接口缺口的情况；后者应补足产品实现或至少保留显式覆盖。",
      "evidenceFiles": [
        "test/dialects/test_dialects.py",
        "core/dialects/openai_responses.py",
        "core/channels/openai_channel.py"
      ],
      "reviewedModules": [
        "test/dialects/test_dialects.py",
        "core/dialects/openai_responses.py",
        "core/channels/openai_channel.py"
      ],
      "recommendedNextAction": "汇总全部未提交改动的风险结论，并给出是否建议合并的最终判断。",
      "recordedAt": "2026-03-19T02:40:10.485Z",
      "findingIds": [
        "F-003"
      ]
    }
  ],
  "findings": [
    {
      "id": "F-001",
      "severity": "high",
      "category": "other",
      "title": "`passthrough_only` 在上游请求发送后才拒绝，可能触发错误的真实上游调用",
      "description": "`core/dialects/router.py` 仅在 `model_handler.request_model()` 返回响应后才检查 `endpoint.passthrough_only`。而 `ModelRequestHandler.request_model()` 在 provider 与入口方言不匹配时会走普通 `process_request()`，因此像 `/v1/messages/count_tokens` 这样的仅透传端点，仍可能先向非 Claude provider 发送一次真实请求，最后才对客户端返回 501。该顺序会导致无意义的上游调用、潜在计费以及副作用。",
      "evidenceFiles": [
        "core/dialects/router.py",
        "core/handler.py",
        "core/dialects/claude.py",
        "core/dialects/registry.py"
      ],
      "relatedMilestoneIds": [
        "m1"
      ],
      "recommendation": "将 `passthrough_only` 的约束前移到 provider 选择或请求分发之前：要么在路由层提前判定仅允许透传兼容 provider，要么在 `request_model()` 内对这类端点直接跳过非透传 provider，确保不会先发请求后拒绝。"
    },
    {
      "id": "F-002",
      "severity": "medium",
      "category": "maintainability",
      "title": "透传子路径后缀解析依赖字面路径前缀匹配，无法自然扩展到参数化主路径",
      "description": "`core/handler.py` 通过 `endpoint.startswith(_ep.full_path)` 为当前子路径寻找基准主端点，再计算 URL 后缀。该算法只对静态主路径稳定成立；如果未来把同一机制复用于包含路径参数的主端点（例如 `/v1/models/{model}:...` 这类形式），字面字符串前缀将无法匹配真实请求路径，导致后缀解析失效。当前方案对 Claude 可用，但其“通用透传根”抽象仍不完整。",
      "evidenceFiles": [
        "core/handler.py",
        "core/dialects/registry.py",
        "core/dialects/router.py",
        "core/dialects/claude.py"
      ],
      "relatedMilestoneIds": [
        "m1"
      ],
      "recommendation": "不要从 `EndpointDefinition.full_path` 的字面字符串反推主路径。建议显式引入 `passthrough_root`/`base_passthrough_path` 元数据，或为透传根单独建模，使子路径拼接基于结构化配置而不是路由模板字符串。"
    },
    {
      "id": "F-003",
      "severity": "medium",
      "category": "test",
      "title": "Responses 解析测试通过收窄输入形态绕开了 `instructions` 未实现问题",
      "description": "修订后的 `test_openai_responses_parse_input_file` 不再验证顶层 `instructions`，而是把 system 内容塞进 `input` 列表中的 system message。与此同时，`parse_responses_request()` 仍只读取 `model`、`input`、`stream` 等字段，没有把 Responses API 常见的顶层 `instructions` 映射为 Canonical system message。结果是测试现在能通过，但真实接口缺口被隐藏了。",
      "evidenceFiles": [
        "test/dialects/test_dialects.py",
        "core/dialects/openai_responses.py",
        "core/channels/openai_channel.py"
      ],
      "relatedMilestoneIds": [
        "m2"
      ],
      "recommendation": "如果产品目标是兼容 Responses API 公开语义，应实现 `instructions -> system message` 的映射；如果暂不支持，则至少保留一个显式测试/文档说明该限制，而不要仅通过改写测试输入形态绕开它。"
    }
  ]
}
<!-- LIMCODE_REVIEW_METADATA_END -->
