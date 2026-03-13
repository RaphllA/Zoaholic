# ContentItem 文件模型更新说明

为了支持多模态文件的统一传输，`ContentItem` 模型已由原先的图片中心模型升级为通用的文件模型。

## 数据结构

### ContentItem

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `type` | `str` | 类型标识。`"text"`, `"image_url"`, `"file"` |
| `text` | `Optional[str]` | 当 type 为 `"text"` 时使用 |
| `image_url` | `Optional[ImageUrl]` | 兼容字段，包含 `url` |
| `file` | `Optional[FileRef]` | **新增**：通用文件引用结构 |

### FileRef

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `mime_type` | `str` | 文件的标准 MIME 类型（如 `application/pdf`, `audio/wav`） |
| `filename` | `str` | 可选的文件名 |
| `data` | `str` | Base64 编码的文件数据（不含 Data URI 前缀） |
| `url` | `str` | 文件的远程 URL 或完整的 Data URI |
| `file_id` | `str` | 用于 OpenAI 等渠道的后端文件 ID |
| `file_uri` | `str` | 用于 Gemini 等渠道的云端存储 URI |

## 开发者建议

1. **优先使用 file 字段**：在编写新插件或适配器时，请优先检查 `item.file`。如果是图片，其 `mime_type` 会以 `image/` 开头。
2. **工具函数**：使用 `core.file_utils` 中的 `get_base64_file` 来统一获取任何类型文件的 Base64 内容，它会自动处理 URL 抓取和 MIME 提取。