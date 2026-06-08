# Open WebUI API 调用指南

## 概述

Open WebUI 提供 **OpenAI 兼容的 RESTful API**，外部应用程序可以通过标准 OpenAI SDK 或 HTTP 请求直接调用，无需通过 Web 界面。

### 基础信息

| 项目 | 值 |
|------|-----|
| **Base URL** | `http://<server-ip>:3000` |
| **API 端点** | `http://<server-ip>:3000/v1/chat/completions` |
| **认证方式** | Bearer Token（在 Web UI 中生成的 API Key） |
| **协议兼容** | OpenAI Chat Completions API |
| **流式支持** | 是（SSE / Server-Sent Events） |

---

## 1. 获取 API Key

### 步骤

1. 使用 LDAP 账号登录 Open WebUI：`http://<server-ip>:3000`
2. 点击右上角 **头像** → **Settings（设置）**
3. 左侧菜单选择 **Account**（不是 General 或 Admin Settings）
4. 页面中找到 **API keys** 区域（可能需要向下滚动）
5. 点击 **Show** 展开后点击 **Create API Key**，输入描述名称（如 "my-app"）
5. 复制生成的 Key（格式类似 `sk-xxxxxxxx...`）

> **注意**：Key 只显示一次，请妥善保存。如丢失需重新生成。

---

## 2. cURL 调用示例

### 2.1 普通请求（非流式）

```bash
curl http://<server-ip>:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model-name>",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### 2.2 流式请求（SSE）

```bash
curl http://<server-ip>:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model-name>",
    "messages": [
      {"role": "user", "content": "请写一首关于春天的诗"}
    ],
    "stream": true
  }'
```

### 2.3 多轮对话

```bash
curl http://<server-ip>:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model-name>",
    "messages": [
      {"role": "system", "content": "你是一个专业的技术助手"},
      {"role": "user", "content": "什么是 Docker？"},
      {"role": "assistant", "content": "Docker 是一个容器化平台..."},
      {"role": "user", "content": "那 Kubernetes 和它有什么关系？"}
    ],
    "stream": true
  }'
```

### 2.4 带 Function Calling（工具调用）

```bash
curl http://<server-ip>:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model-name>",
    "messages": [
      {"role": "user", "content": "北京今天天气怎么样？"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取指定城市的天气信息",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {
                "type": "string",
                "description": "城市名称"
              }
            },
            "required": ["city"]
          }
        }
      }
    ]
  }'
```

---

## 3. Python 调用示例

### 3.1 使用官方 openai 库（推荐）

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://<server-ip>:3000/v1",
    api_key="sk-your-api-key-here"
)

# 非流式调用
response = client.chat.completions.create(
    model="<model-name>",
    messages=[
        {"role": "user", "content": "你好！"}
    ]
)
print(response.choices[0].message.content)

# 流式调用
stream = client.chat.completions.create(
    model="<model-name>",
    messages=[
        {"role": "user", "content": "写一段代码"}
    ],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
print()
```

### 3.2 使用 requests 库

```python
import requests

url = "http://<server-ip>:3000/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-your-api-key-here",
    "Content-Type": "application/json"
}
payload = {
    "model": "<model-name>",
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "stream": False
}

response = requests.post(url, headers=headers, json=payload)
data = response.json()
print(data["choices"][0]["message"]["content"])
```

### 3.3 流式调用（requests + SSE）

```python
import requests

url = "http://<server-ip>:3000/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-your-api-key-here",
    "Content-Type": "application/json"
}
payload = {
    "model": "<model-name>",
    "messages": [{"role": "user", "content": "讲个故事"}],
    "stream": True
}

response = requests.post(url, headers=headers, json=payload, stream=True)

for line in response.iter_lines():
    line = line.decode("utf-8")
    if line.startswith("data: ") and line != "data: [DONE]":
        import json
        chunk = json.loads(line[6:])
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        if "content" in delta:
            print(delta["content"], end="", flush=True)
print()
```

---

## 4. Node.js 调用示例

### 4.1 使用 openai SDK

```javascript
const OpenAI = require('openai');

const client = new OpenAI({
  baseURL: 'http://<server-ip>:3000/v1',
  apiKey: 'sk-your-api-key-here'
});

async function chat() {
  const stream = await client.chat.completions.create({
    model: '<model-name>',
    messages: [{ role: 'user', content: 'Hello!' }],
    stream: true
  });

  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
}

chat();
```

### 4.2 使用 fetch（原生）

```javascript
async function chat() {
  const response = await fetch('http://<server-ip>:3000/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer sk-your-api-key-here',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: '<model-name>',
      messages: [{ role: 'user', content: 'Hello' }],
      stream: false
    })
  });
  const data = await response.json();
  console.log(data.choices[0].message.content);
}

chat();
```

---

## 5. 支持的 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/models` | GET | 获取可用模型列表 |
| `/v1/chat/completions` | POST | 对话补全（主要接口） |
| `/v1/completions` | POST | 文本补全 |
| `/v1/embeddings` | POST | 文本向量化 |
| `/v1/files` | GET/POST | 文件管理 |
| `/v1/messages` | POST | Anthropic 兼容端点 |

### 获取模型列表

```bash
curl http://<server-ip>:3000/v1/models \
  -H "Authorization: Bearer sk-your-api-key-here"
```

返回示例：

```json
{
  "data": [
    {
      "id": "qwen3-32b",
      "object": "model",
      "owned_by": "open-webui"
    }
  ]
}
```

---

## 6. 请求参数说明

### Chat Completions 核心参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型名称（从 `/v1/models` 获取） |
| `messages` | array | 是 | 对话消息数组 |
| `stream` | boolean | 否 | 是否使用流式输出（默认 `false`） |
| `temperature` | number | 否 | 温度参数 0~2（默认 `1`） |
| `max_tokens` | integer | 否 | 最大生成 token 数 |
| `top_p` | number | 否 | 核采样概率（默认 `1`） |
| `stop` | string/array | 否 | 停止生成的标记 |
| `tools` | array | 否 | 工具/函数定义列表 |

### Messages 结构

```json
[
  { "role": "system", "content": "系统提示词" },
  { "role": "user", "content": "用户输入" },
  { "role": "assistant", "content": "助手回复" },
  { "role": "user", "content": "继续对话..." }
]
```

---

## 7. 常见问题排查

### 401 Unauthorized

- **原因**：API Key 无效或未提供
- **解决**：检查 Header 中 `Authorization: Bearer <key>` 是否正确

### 403 Forbidden

- **原因**：该 Key 没有权限访问指定模型或端点
- **解决**：联系管理员确认模型访问权限

### 404 Not Found

- **原因**：模型名称不存在或端点路径错误
- **解决**：先调用 `/v1/models` 确认可用模型列表

### 500 Internal Server Error

- **原因**：后端推理服务异常
- **解决**：检查 vLLM 服务状态和日志

### 流式输出无响应

- **原因**：客户端未正确处理 SSE 数据格式
- **解决**：确保逐行解析 `data: {...}` 格式的行，以 `data: [DONE]` 结束

---

## 8. 当前部署环境

| 项目 | 值 |
|------|-----|
| **Server** | `cnt-aisrvp01` (`10.224.10.12`) |
| **端口** | `3000` |
| **Base URL** | `http://10.224.10.12:3000/v1` |
| **后端推理** | vLLM @ `10.224.10.12:8203`, `10.224.10.12:8202` |
| **认证** | LDAP（域账号）+ API Key |
| **注册** | 已关闭（仅 LDAP 登录） |

---

## 9. 快速测试命令

复制以下命令到终端快速验证 API 可用性（替换 `<your-api-key>` 和 `<model-name>`）：

```bash
curl http://10.224.10.12:3000/v1/models \
  -H "Authorization: Bearer <your-api-key>" | python -m json.tool
```
