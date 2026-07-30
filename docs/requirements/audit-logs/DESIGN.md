# 管理员审计日志页面设计

## 目标与范围

为管理员提供审计日志的检索、筛选和详情查看页面，用于排查
`/api/v1/chat/completions` 等受审计请求。数据来源是已由审计中间件持续写入的 `audit_log`
数据库表，不读取或解析 `audit.log` 文件。数据库 schema 截至 migration
`b9c0d1e2f3a4`。

本期仅提供管理员查询：不提供普通用户访问、实时追踪、日志编辑、日志删除或正文批量导出。

## 信息架构

- 路由：`/admin/audit-logs`
- 管理端顶部导航新增 `Audit Logs`，置于 `Evaluations` 后、`Functions` 前。
- 复用现有管理员布局：紧凑顶部导航、全宽内容区、浅色/深色主题。
- 后端路由必须使用管理员鉴权；非管理员保持现有行为，重定向到首页或返回 `403`。

## 页面布局

页面不使用营销式页面卡片。内容从上到下为筛选工具栏、活动筛选条件、结果表格和分页控件。
默认排序为最新记录在前。

### 筛选工具栏

工具栏保持现有 Users 与 Feedbacks 页面约 `h-8` 的紧凑高度。

左侧为带 Search 图标的单行输入框：

- 占据可用宽度，placeholder 为 `Search path, user, IP, or request ID`。
- 输入后 300ms 防抖，自动刷新并回到第一页。
- 有内容时显示 X 图标按钮以清空。

右侧为三个工具控件：

1. 时间范围下拉：`Last 24 hours`、`Last 7 days`、`Last 30 days`、`Custom range`。
   默认 `Last 24 hours`；自定义范围打开两个日期时间输入。
2. Filters 图标按钮，带 tooltip。点击后在工具栏下展开筛选区；有非默认筛选时显示
   强调状态和筛选数量。
3. Reset 图标按钮，仅在存在非默认条件时显示，清空查询和所有筛选。

筛选区采用无外层卡片的细分隔栏，窄屏时纵向排列，宽屏为两行紧凑网格：

| 条件 | 控件 | 行为 |
|---|---|---|
| Endpoint | 可搜索单选 | 默认全部；候选值来自当前日期范围的服务端 facet |
| User | 远程搜索组合框 | 按姓名、邮箱或 ID 搜索；选择后以 chip 显示 |
| Request model | 可搜索单选 | 筛选 `request_model`；候选值来自当前日期范围的服务端 facet |
| Response model | 可搜索单选 | 筛选 `response_model`；候选值来自当前日期范围的服务端 facet |
| Request skills | 可搜索多选 | 筛选 JSON `request_skill_ids`；选择多个值时匹配含任一选定 Skill ID 的记录 |
| Status | 多选菜单 | `2xx`、`4xx`、`5xx`、`No response` |
| Source IP | 文本输入 | 精确匹配或 CIDR 前缀匹配由 API 明确声明 |
| Body state | 多选菜单 | `Request captured`、`Response captured`、`Truncated` |

已生效条件在筛选栏下显示为可移除 chip；chip 内使用 X 图标。筛选条件变动后立即重新查询，
不设置独立的提交按钮。

### 结果表格

沿用现有管理表格样式：透明背景、细底部分隔线、小号大写表头、行 hover、横向滚动。
每页固定 30 条，使用现有 `Pagination.svelte` 外观。

| 列 | 展示 |
|---|---|
| Time | 本地绝对时间；窄屏只显示相对时间，hover 显示完整时间 |
| User | 姓名优先，其次邮箱，再其次 `Anonymous`；次行显示截断后的 ID |
| Endpoint | 等宽字体，单行截断；hover 显示完整路径 |
| Method | 紧凑中性色 badge |
| Status | 状态码与颜色点：2xx 绿色、4xx 琥珀色、5xx 红色、无响应灰色 |
| Source | IP；没有 IP 时显示短横线 |
| Level | `Metadata`、`Request` 或 `Request + Response` 的低对比度标签 |
| Details | Eye 图标按钮和 tooltip |

`Time`、`User`、`Endpoint`、`Status` 支持排序，复用现有升降序箭头和 `aria-sort`。
点击行或 Details 图标均打开详情，不在行内展开正文。

空状态沿用现有 Evaluations 的居中布局：`No audit logs found` 和
`Try adjusting your search or filters.`。加载态使用现有 Spinner；刷新已有结果时保留旧表格，
仅在工具栏显示小型 loading 指示，避免页面跳动。

### 详情模态框

复用现有 `Modal` 的标题栏、关闭 X 图标和底部 Close 按钮；桌面端使用 `lg` 宽度，
移动端占据可用视口。列表接口不返回正文，打开模态框后才请求详情。

详情分为三个无嵌套卡片的区段：

1. Request：时间、请求 ID、用户快照、方法、完整脱敏 URI、来源 IP、User-Agent、审计级别，及
   `request_model`、`request_extra`、`request_skill_ids`、`request_tool_ids`、
   `request_response_format`、`request_extra_body`、`request_system_messages`、
   `request_user_messages`。
2. Response：HTTP 状态、是否截断、响应正文是否被捕获，及 `response_id`、`response_model`、
   `response_finish_reasons`。
3. Captured content：请求和响应各自的可折叠等宽文本区；仅在对应正文存在时展示。拆分 JSON 字段
   同样以等宽纯文本展示，保留数组及多模态 content 的原始结构。

正文默认折叠为 12 行，展开后最大高度为 `24rem` 并可滚动。每个可复制值旁使用 Copy 图标
按钮和 tooltip。正文原样显示为文本，不能作为 HTML 渲染。脱敏字段显示 `********`，截断内容
末尾显示 `Captured content was truncated`。

## 数据与 API 合约

所有接口位于 `/api/v1/audit-logs`，需要管理员 Bearer token。

### 列表

`GET /api/v1/audit-logs`

```text
start_at=<unix-ms>&end_at=<unix-ms>
q=<search text>&user_id=<id>&endpoint=<path>
request_model=<model>&response_model=<model>
request_skill_ids=<id1>,<id2>&status_classes=2xx,5xx
source_ip=<value>
body_state=request,response,truncated
order_by=created_at&direction=desc&page=1&limit=30
```

响应不含 `request_object`、`response_object` 和完整 `user_agent`：

```json
{
  "items": [
    {
      "id": "uuid",
      "created_at": 1780000000000,
      "user": { "id": "...", "name": "...", "email": "..." },
      "verb": "POST",
      "request_path": "/api/v1/chat/completions",
      "response_status_code": 200,
      "source_ip": "203.0.113.10",
      "audit_level": "REQUEST",
      "request_captured": true,
      "response_captured": false,
      "request_truncated": false,
      "response_truncated": false
    }
  ],
  "total": 124
}
```

### 详情与 facet

`GET /api/v1/audit-logs/{id}` 返回列表字段加上脱敏后的 `request_uri`、`user_agent`、
`request_object`、`response_object`、`user_snapshot`、请求拆分字段 `request_model`、
`request_extra`、`request_skill_ids`、`request_tool_ids`、`request_response_format`、
`request_extra_body`、`request_system_messages`、`request_user_messages`，以及响应拆分字段
`response_id`、`response_model`、`response_finish_reasons` 和正文截断状态。

`GET /api/v1/audit-logs/facets?start_at=&end_at=` 返回有限的 endpoint、`request_model`、
`response_model`、`request_skill_ids` 与状态分类候选值；不返回完整用户集合。用户组合框沿用
管理员用户搜索接口。

服务端必须为筛选、排序和分页参数设置白名单；不接受任意列名或原始 SQL 条件。

## 权限与隐私

- 路由、列表、详情、facet 均使用管理员鉴权。
- 正文不出现在列表、浏览器标题、URL 参数、toast 或前端日志中。
- 页面明确标示正文可能包含 Prompt、模型输出和敏感业务数据；本期不提供导出。
- 所有展示数据来自数据库已脱敏值；前端不承担脱敏责任。
- 拆分字段从已脱敏、受正文捕获上限约束的数据中派生。`REQUEST` 级别没有响应拆分值；截断、
  非 JSON 或无法完整解析的 SSE 正文可使部分拆分值为 `NULL`。历史记录不回填。
- 用户删除后不级联删除审计记录；用户快照保证历史记录可解释。

## 实现落点

前端新增：

- `src/routes/(app)/admin/audit-logs/+page.svelte`
- `src/lib/components/admin/AuditLogs.svelte`
- `src/lib/components/admin/AuditLogs/FilterBar.svelte`
- `src/lib/components/admin/AuditLogs/DetailModal.svelte`
- `src/lib/apis/audit-logs/index.ts`

修改 `src/routes/(app)/admin/+layout.svelte` 增加导航入口；所有可见字符串进入 i18n 资源。
后端依赖数据库审计表、管理员查询 router 和按 ID 的详情查询，不在本次页面设计中实现。

## 验收标准

1. 管理员可按默认时间范围看到最新记录，并按 endpoint、用户、方法、状态和 IP 组合过滤。
2. 普通用户无法访问路由或调用 API。
3. 列表不传输请求或响应正文；仅打开详情才加载脱敏正文。
4. 时间、用户、endpoint、状态排序正确，切换筛选时分页回到第一页。
5. 窄屏下筛选垂直排列，表格可横向滚动，详情可完整浏览和关闭。
