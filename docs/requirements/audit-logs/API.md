# 审计日志后端查询 API 规范

## 1. 概述与鉴权要求

为满足 Open WebUI 管理员在前端对审计日志进行多维筛选、检索与查看单条详情的需求，后端需要提供一组专门的审计查询 RESTful API。

### 权限与安全

- **访问限制**：所有审计查询接口必须使用管理员鉴权（Bearer Token，用户角色为 `admin`）。非管理员调用直接返回 `403 Forbidden`。
- **正文保护**：请求正文（`request_object`）与响应正文（`response_object`）属于敏感内容，**不得**包含在列表查询响应中。正文仅在管理员明确请求单条详情接口（`GET /api/v1/audit-logs/{id}`）时返回。
- **脱敏原则**：接口展示的所有正文与 URI 数据均直接来自数据库 `audit_log` 表中已脱敏的记录。后端不得在查询时解密或二次暴露原始敏感数据（如密码、Token、API Key）。

---

## 2. 接口列表

| HTTP 方法 | 接口路径 | 功能描述 |
|---|---|---|
| `GET` | `/api/v1/audit-logs` | 审计日志列表查询（支持多条件筛选、搜索、排序与分页） |
| `GET` | `/api/v1/audit-logs/{id}` | 查询单条审计日志的完整详情（含已脱敏的正文与解析字段） |
| `GET` | `/api/v1/audit-logs/facets` | 获取当前时间范围内的筛选候选值（Endpoint、Model、Skill ID、状态等） |

---

## 3. 接口详细定义

### 3.1 审计日志列表查询

**接口地址**：`GET /api/v1/audit-logs`

**说明**：根据传入的筛选条件返回分页的审计日志摘要列表。响应体中隐去请求/响应正文、完整 User-Agent 和完整 URI。

#### Request Query Parameters

| 参数名 | 类型 | 是否必填 | 默认值 | 示例 / 说明 |
|---|---|---|---|---|
| `start_at` | integer | 否 | 24小时前毫秒 | Unix 毫秒时间戳，检索起始时间点 |
| `end_at` | integer | 否 | 当前毫秒 | Unix 毫秒时间戳，检索截止时间点（`start_at` $\le$ `end_at`） |
| `q` | string | 否 | - | 模糊搜索关键字，匹配 `request_path`、用户姓名/邮箱/ID、`source_ip` 或 `id` |
| `user_id` | string | 否 | - | 精确匹配用户 ID |
| `endpoint` | string | 否 | - | 精确匹配 API 路径，如 `/api/v1/chat/completions` |
| `request_model` | string | 否 | - | 精确匹配请求模型名称（拆分字段 `request_model`） |
| `response_model` | string | 否 | - | 精确匹配响应模型名称（拆分字段 `response_model`） |
| `request_skill_ids` | string | 否 | - | 多选 Skill ID，逗号分隔，如 `skill-a,skill-b`（任一匹配） |
| `status_classes` | string | 否 | - | HTTP 状态分类，逗号分隔，如 `2xx,4xx,5xx,no_response` |
| `source_ip` | string | 否 | - | 来源 IP 匹配（支持精确匹配或前缀匹配） |
| `body_state` | string | 否 | - | 正文状态分类，逗号分隔：`request`（请求捕获）、`response`（响应捕获）、`truncated`（被截断） |
| `order_by` | string | 否 | `created_at` | 排序字段，白名单：`created_at`, `request_path`, `response_status_code`, `user_id` |
| `direction` | string | 否 | `desc` | 排序方向：`asc` 或 `desc` |
| `page` | integer | 否 | 1 | 页码（从 1 开始） |
| `limit` | integer | 否 | 30 | 每页条数（最大值 100，默认 30） |

#### Response (`200 OK`)

```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "created_at": 1780000000000,
      "user": {
        "id": "u-12345",
        "name": "Alice Smith",
        "email": "alice@example.com"
      },
      "verb": "POST",
      "request_path": "/api/v1/chat/completions",
      "response_status_code": 200,
      "source_ip": "203.0.113.10",
      "audit_level": "REQUEST_RESPONSE",
      "request_captured": true,
      "response_captured": true,
      "request_truncated": false,
      "response_truncated": false
    }
  ],
  "total": 124,
  "page": 1,
  "limit": 30
}
```

---

### 3.2 单条审计日志详情

**接口地址**：`GET /api/v1/audit-logs/{id}`

**说明**：根据审计日志 UUID 查询完整的单条记录，包含已脱敏的请求正文、响应正文以及拆分的元数据字段。

#### Path Parameters

- `id`: string (UUID)，审计日志记录的主键 ID。

#### Response (`200 OK`)

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": 1780000000000,
  "user": {
    "id": "u-12345",
    "name": "Alice Smith",
    "email": "alice@example.com"
  },
  "user_snapshot": {
    "id": "u-12345",
    "name": "Alice Smith",
    "email": "alice@example.com",
    "role": "user"
  },
  "verb": "POST",
  "request_path": "/api/v1/chat/completions",
  "request_uri": "/api/v1/chat/completions?stream=true",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
  "source_ip": "203.0.113.10",
  "response_status_code": 200,
  "audit_level": "REQUEST_RESPONSE",

  "request_captured": true,
  "request_truncated": false,
  "request_object": "{\"model\": \"gpt-4o\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}",
  "request_model": "gpt-4o",
  "request_extra": null,
  "request_skill_ids": ["skill-calc"],
  "request_tool_ids": [],
  "request_response_format": null,
  "request_extra_body": null,
  "request_system_messages": [],
  "request_user_messages": ["Hello"],

  "response_captured": true,
  "response_truncated": false,
  "response_object": "{\"id\": \"chatcmpl-999\", \"choices\": [{\"finish_reason\": \"stop\", \"message\": {\"content\": \"Hi!\"}}]}",
  "response_id": "chatcmpl-999",
  "response_model": "gpt-4o-2024-05-13",
  "response_finish_reasons": ["stop"]
}
```

---

### 3.3 筛选候选值（Facets）获取

**接口地址**：`GET /api/v1/audit-logs/facets`

**说明**：用于在前端筛选面板中动态加载可选的 Endpoint、模型名称、Skill ID 以及状态码统计分类。

#### Request Query Parameters

| 参数名 | 类型 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `start_at` | integer | 否 | 24小时前毫秒 | 统计候选值的起始时间 |
| `end_at` | integer | 否 | 当前毫秒 | 统计候选值的截止时间 |

#### Response (`200 OK`)

```json
{
  "endpoints": [
    "/api/v1/chat/completions",
    "/api/v1/models",
    "/api/v1/embeddings"
  ],
  "request_models": [
    "gpt-4o",
    "claude-3-5-sonnet",
    "llama-3-70b"
  ],
  "response_models": [
    "gpt-4o-2024-05-13",
    "claude-3-5-sonnet-20240620"
  ],
  "request_skill_ids": [
    "web_search",
    "code_interpreter",
    "calculator"
  ],
  "status_classes": [
    "2xx",
    "4xx",
    "5xx",
    "no_response"
  ]
}
```

---

## 4. 错误处理与状态码规范

| 状态码 | 原因描述 | 响应示例 |
|---|---|---|
| `401 Unauthorized` | 缺少 Authorization 头部或 Token 已失效 | `{"detail": "Not authenticated"}` |
| `403 Forbidden` | 当前访问用户不是管理员角色 | `{"detail": "Admin privilege required"}` |
| `404 Not Found` | 指定 ID 的审计记录不存在 | `{"detail": "Audit log entry not found"}` |
| `422 Unprocessable Entity` | 查询参数校验失败（如非法排序列、`start_at > end_at` 或非法的分页限制） | `{"detail": [{"loc": ["query", "order_by"], "msg": "Invalid order_by field"}]}` |
