# 审计日志管理页面 PRD

## 文档信息

| 项目 | 内容 |
|---|---|
| 需求名称 | 管理员审计日志查询与过滤 |
| 状态 | 待实现 |
| 目标版本 | 待排期 |
| 关联设计 | `docs/requirements/audit-logs/DESIGN.md` |
| 后端基线 | `4245071e9 feat(audit): persist API audit logs to database`，迁移截至 `b9c0d1e2f3a4` |

## 背景

Open WebUI 已支持对 HTTP 请求进行审计，并可同时写入 JSON Lines 文件与应用数据库。
管理员当前只能通过直接访问 `audit.log` 或数据库客户端查看记录，无法在 WebUI 中按时间、
调用方、端点和状态码高效查询，也无法安全地按需查看已脱敏的请求与响应内容。

本需求提供一个仅管理员可访问的审计日志页面，将现有 `audit_log` 数据转化为可筛选、可分页
和可追溯的管理能力。它不改变模型调用逻辑、聊天持久化逻辑或已有审计记录的写入语义。

## 已完成的后端能力

以下能力已经在后端基线中交付，是本需求的依赖而非重复交付内容：

- Alembic migration `c2a4f28d7b1e` 创建 `audit_log` 表及时间、路径、用户、状态索引；
  `e6f7a8b9c0d1`、`f7a8b9c0d1e2`、`a8b9c0d1e2f3`、`b9c0d1e2f3a4` 依次扩展、规范并排列
  请求与响应拆分字段。
- `AuditLoggingMiddleware` 在受审计请求完成后写入一条数据库记录；数据库写入失败不会改变
  原请求的响应。
- 记录包含请求 ID、Unix 毫秒时间、用户快照、审计级别、方法、路径、脱敏 URI、状态码、IP、
  User-Agent、已捕获的请求/响应正文及截断标志。
- `ENABLE_AUDIT_LOGS_DB=true` 开启数据库写入；文件日志可继续通过
  `ENABLE_AUDIT_LOGS_FILE=true` 保留，形成双写。
- `AUDIT_EXACT_INCLUDED_PATHS=/api/v1/chat/completions` 会严格只审计该路径，并优先于通用
  包含/排除规则和认证端点的强制审计规则。
- JSON 字段中 `password`、`authorization`、`cookie`、`api_key`、`token`、`secret` 及相应
  后缀字段已在写入前脱敏。
- 已捕获的请求正文会额外保存 `request_model`、`request_extra`、`request_skill_ids`、
  `request_tool_ids`、`request_response_format`、`request_extra_body`，以及
  `request_system_messages`、`request_user_messages` 两个按消息顺序排列的内容数组。
- 已捕获的响应正文会额外保存 `response_id`、`response_model` 和
  `response_finish_reasons`。后者保留全部 `choices[].finish_reason`，以支持多 choice 响应；
  OpenAI SSE 流式分片也会尝试提取这些字段。
- 拆分值派生自已脱敏、受 `MAX_BODY_LOG_SIZE` 限制的正文。`METADATA` 或 `REQUEST` 级别不会
  写入响应拆分值；截断或非 JSON 正文可能无法提取全部字段。历史记录不回填。

当前缺口：没有 `audit_log` 的管理员查询 router、详情接口、前端 API 封装、导航入口或页面。

## 目标

1. 让管理员无需直接连接数据库即可查询审计记录。
2. 支持快速定位某个 API 调用、调用人、调用来源或失败响应。
3. 默认保护请求/响应正文，仅在管理员主动打开单条详情时传输。
4. 复用 Open WebUI 现有管理端表格、筛选、分页、模态框和 i18n 模式。

## 非目标

- 不向普通用户、聊天所有者或 API 调用者开放审计记录。
- 不提供实时 tail、全文检索引擎、跨实例聚合、修改记录或删除记录。
- 不读取、迁移或回填历史 `audit.log` 文件。
- 不提供请求/响应正文的默认列表展示、批量下载或导出。
- 不在请求处理路径执行审计日志保留期清理。

## 用户与核心场景

| 角色 | 场景 | 成功结果 |
|---|---|---|
| 系统管理员 | 某 API 客户端报告调用失败 | 按时间、端点和 `5xx` 筛选，定位对应状态与来源 IP |
| 系统管理员 | 排查某用户的调用行为 | 按用户搜索并查看调用时间、路径和结果 |
| 系统管理员 | 核对某次请求的脱敏内容 | 从列表打开单条详情，按需查看捕获的请求/响应正文 |
| 系统管理员 | 验证外部 API 与网页聊天已分流审计 | 过滤 `/api/v1/chat/completions`，确认不存在网页 `/api/chat/completions` 记录 |

## 功能需求

### 1. 访问与导航

- 管理端新增 `/admin/audit-logs` 路由和 `Audit Logs` 顶部导航项。
- 页面、列表 API、详情 API 和 facet API 都必须使用管理员鉴权。
- 非管理员访问页面时使用现有管理端行为跳转首页；直接访问 API 返回 `403`。
- 页面标题遵循现有管理端格式：`Audit Logs / {WEBUI_NAME}`。

### 2. 列表与分页

- 初始加载默认查询过去 24 小时，按 `created_at desc` 排序，每页 30 条。
- 列表展示时间、用户、端点、方法、状态、来源 IP、审计级别和详情入口。
- 列表响应不得包含 `request_object`、`response_object`、完整 `user_agent` 或完整 URI。
- 支持按时间、用户、端点和状态排序；仅允许服务端定义的排序字段与方向。
- 筛选条件或排序变更时回到第一页；加载中保留上一轮结果以减少页面跳动。
- 无结果、首次加载和请求失败分别使用现有空状态、Spinner 与 toast 模式。

### 3. 查询与过滤

支持以下条件并可组合使用：

| 条件 | 要求 |
|---|---|
| 时间范围 | 24 小时、7 天、30 天和自定义日期时间范围 |
| 关键字 | 查询路径、用户姓名/邮箱/ID、来源 IP 或请求 ID |
| Endpoint | 从当前时间范围的服务端 facet 选择 |
| User | 按姓名、邮箱或 ID 的远程搜索组合框 |
| Request model | 从当前时间范围的服务端 facet 搜索并单选 `request_model` |
| Response model | 从当前时间范围的服务端 facet 搜索并单选 `response_model` |
| Request skills | 从当前时间范围的服务端 facet 搜索并多选 `request_skill_ids`；多个值按任一匹配 |
| Status | `2xx`、`4xx`、`5xx`、无响应多选 |
| Source IP | 精确匹配或服务端明确支持的前缀匹配 |
| Body state | 请求已捕获、响应已捕获、正文被截断 |

- 关键字输入使用 300ms 防抖。
- 筛选区域默认收起，活动条件以可移除 chip 显示。
- 有筛选条件时提供图标型 Reset 控件，清空查询和全部条件。

### 4. 单条详情

- 点击表格行或 Eye 图标后，根据 ID 请求详情；不得提前批量加载正文。
- 详情显示请求元数据、响应状态、截断状态、用户快照、已捕获内容及可查询的拆分字段。
- 详情中的请求字段分组展示 `request_model`、`request_extra`、`request_skill_ids`、
  `request_tool_ids`、`request_response_format`、`request_extra_body`、`request_system_messages`、
  `request_user_messages`；响应字段分组展示 `response_id`、`response_model`、
  `response_finish_reasons`。JSON 值必须以纯文本展示，不得渲染为 HTML。
- 请求/响应正文以纯文本、等宽、可折叠和可滚动的方式呈现，绝不作为 HTML 渲染。
- 详情字段提供 Copy 图标按钮；正文、URI 和 User-Agent 均保持后端已脱敏值。
- 未在当前审计级别捕获的正文显示明确的“未捕获”状态，而非空白内容。

### 5. 管理端 API

新增以下管理员 API：

| API | 用途 |
|---|---|
| `GET /api/v1/audit-logs` | 条件筛选、排序、分页的列表数据 |
| `GET /api/v1/audit-logs/{id}` | 单条完整详情，含已脱敏正文 |
| `GET /api/v1/audit-logs/facets` | 当前时间范围的端点、请求模型、响应模型、请求 Skill ID 和状态候选值 |

列表参数：

```text
start_at, end_at, q, user_id, endpoint, request_model, response_model,
request_skill_ids, status_classes, source_ip, body_state, order_by, direction, page, limit
```

- `limit` 最大 100，默认和页面均使用 30。
- 日期使用 Unix 毫秒；`start_at` 不得晚于 `end_at`。
- 任何未知参数、无效状态分类、无效排序列或超出范围的分页值返回 `422`。
- facet 接口只返回有限候选值，用户条件复用已有管理员用户搜索能力，避免传输完整用户表。

## 数据与隐私要求

- UI 只读取数据库审计记录，不直接访问宿主机文件系统或 SQLite 文件。
- `user_snapshot` 是历史快照；用户被删除后记录仍可查询。
- 记录仅保存写入时的数据，不对已存在记录重新脱敏或更新。
- 拆分字段与原始正文具有相同的敏感数据边界：仅从已脱敏正文派生，默认只在管理员详情中传输。
- 页面不得在浏览器控制台、URL、标题、错误 toast 中输出正文或完整敏感字段。
- 页面不提供导出；若后续提出导出需求，必须单独评估权限、字段白名单、范围上限和审计链。
- 运维保留期继续由外部数据库任务或备份策略处理；本需求不新增自动删除任务。

## 体验与可访问性要求

- 复用现有管理端的紧凑工具栏、透明表格、排序箭头、`Pagination.svelte`、Tooltip、Badge 与
  Modal，不引入独立设计系统。
- 适配浅色与深色主题，状态颜色不能作为唯一信息来源。
- 所有图标按钮都有可本地化 `aria-label` 与 tooltip。
- 窄屏下筛选控件纵向排列，结果表格保留横向滚动，详情模态框使用可用视口宽度。
- 所有新增展示文案接入现有 i18n 机制。

## 实现范围

前端：

- `src/routes/(app)/admin/audit-logs/+page.svelte`
- `src/lib/components/admin/AuditLogs.svelte`
- `src/lib/components/admin/AuditLogs/FilterBar.svelte`
- `src/lib/components/admin/AuditLogs/DetailModal.svelte`
- `src/lib/apis/audit-logs/index.ts`
- `src/routes/(app)/admin/+layout.svelte` 和 i18n 资源

后端：

- 新增管理员 audit log router、查询服务和响应模型。
- 将 router 注册到 `/api/v1/audit-logs`。
- 复用已有 `AuditLog` 模型及其请求/响应拆分字段；不修改审计写入、迁移或双写行为。
- 为筛选、排序、权限、正文延迟加载和边界值补充测试。

## 验收标准

1. 配置 `ENABLE_AUDIT_LOGS_DB=true` 后，管理员可在页面看到数据库中最新的审计记录。
2. 非管理员不能访问页面或任一审计查询 API。
3. `/api/v1/chat/completions` 的记录可按端点、时间、用户、状态和 IP 筛选；多条件结果正确。
4. 列表响应和浏览器网络预览不包含请求或响应正文；打开详情后才请求正文。
5. 已截断、未捕获和无响应的记录具有明确且可访问的视觉状态。
6. 页面在移动端无内容重叠，表格可横向滚动，详情内容可滚动和复制。
7. 新查询能力不改变审计写入失败不影响原 API 响应的既有保证。

## 发布与验证

1. 部署包含 migration `b9c0d1e2f3a4` 的版本，确认应用启动完成数据库升级。
2. 以双写配置启用数据库审计并发送受审计请求。
3. 使用管理员账户验证列表、筛选、详情和权限控制；使用普通账户验证拒绝访问。
4. 比对 `audit_log`、页面列表和文件审计日志的同一请求 ID，确认数据一致；验证请求模型、响应模型
   和请求 Skill ID 过滤结果正确。
5. 验证普通 JSON 与 SSE 响应的 `response_id`、`response_model`、`response_finish_reasons`，以及
   长正文截断时拆分字段为空或不完整但原 Chat Completions 响应不受影响。
