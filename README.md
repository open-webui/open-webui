# Open WebUI (Custom Edition)

<p align="center">
  <img src="./banner.png" alt="Open WebUI Banner" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/ztx888/open-webui">
    <img src="https://img.shields.io/badge/Fork-ztx888%2Fopen--webui-blue?style=for-the-badge&logo=github" alt="Fork Badge"/>
  </a>
  <a href="https://github.com/open-webui/open-webui">
    <img src="https://img.shields.io/badge/Upstream-open--webui-green?style=for-the-badge&logo=github" alt="Upstream Badge"/>
  </a>
  <img src="https://img.shields.io/badge/Version-v0.7.3--1-orange?style=for-the-badge&logo=git" alt="Version"/>
  <img src="https://img.shields.io/badge/Arch-x86__64%20%7C%20ARM64-blueviolet?style=for-the-badge&logo=docker" alt="Arch Badge"/>
</p>

<p align="center">
  <b>功能增强 · 深度汉化 · 多架构支持</b>
</p>

---

## 📖 简介

本项目基于优秀的 [Open WebUI](https://github.com/open-webui/open-webui) 构建，旨在提供**更强的模型能力集成**、**更精细的运营控制**以及**更流畅的中文体验**。我们紧密跟随上游更新，同时持续增添实用的扩展功能。

### 为什么选择这个版本？

| 场景 | 解决方案 |
|:-----|:---------|
| 想要使用 OpenAI 最新的 Responses API 和推理模型？ | ✅ 首发支持，实时展示思考过程 |
| Gemini 接口经过中间层转换丢失特性？ | ✅ 原生 SDK 直连，完整保留所有参数 |
| 需要精确控制 API 成本？ | ✅ 按次/Token 计费，区分输入输出价格 |
| 在树莓派或 ARM 服务器上部署？ | ✅ 提供专门优化的 ARM64 镜像 |
| 中文界面翻译不准确？ | ✅ 深度本地化，专业术语校对 |

---

## 🚀 快速开始

### Docker 一键部署

#### x86_64 架构 (Intel/AMD)

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest
```

#### ARM64 架构 (Apple Silicon / 树莓派 / Orange Pi / 飞牛 NAS 等)

> ⚠️ **重要提示**：ARM64 设备必须使用带有 `-arm64` 后缀的镜像标签！

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest-arm64
```

#### Docker Compose

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'
services:
  open-webui:
    image: ghcr.io/ztx888/openwebui:latest  # ARM64 设备请改为 latest-arm64
    container_name: open-webui
    ports:
      - "3000:8080"
    volumes:
      - open-webui:/app/backend/data
    restart: always

volumes:
  open-webui:
```

启动服务：
```bash
docker compose up -d
```

### 镜像标签说明

| 标签 | 架构 | 适用设备 |
|:-----|:-----|:---------|
| `latest` | x86_64 (amd64) | Intel/AMD 服务器、PC、大部分云服务器 |
| `latest-arm64` | ARM64 (aarch64) | Apple Silicon Mac、树莓派 4/5、Orange Pi、飞牛 NAS、华为鲲鹏等 |
| `git-{sha}` | x86_64 | 特定提交版本 |
| `git-{sha}-arm64` | ARM64 | 特定提交版本 (ARM) |

---

## ✨ 核心特性

### 🧠 模型能力深度集成

| | |
| :--- | :--- |
| **OpenAI Responses API**<br>首发支持 OpenAI 新版 `/v1/responses` 接口：<br>- 流式输出思考过程 (Reasoning Content)<br>- 支持 o1、o3 等推理模型<br>- 实时展示模型的推理步骤 | **Google Gemini 原生**<br>直连官方 SDK，无需中间层转换：<br>- 支持 `thinking_budget` 等原生参数<br>- Gemini 2.5 Pro / Gemini 3 完美兼容<br>- 原生工具调用 (Function Calling) |
| **推理强度控制**<br>为 o1/o3 等模型配置 **Reasoning Effort**：<br>- Low / Medium / High 三档预设<br>- 支持自定义数值输入<br>- 灵活平衡速度与质量 | **智能图像编辑**<br>优化的图像编辑上下文管理：<br>- 自动精简历史消息<br>- 保留必要的图像引用<br>- 大幅节省 Token 消耗 |

### 🛠️ 系统管理增强

| | |
| :--- | :--- |
| **精细化计费系统**<br>运营级成本控制方案：<br>- 按次计费 / 按 Token 计费<br>- 区分输入、输出、推理价格<br>- 实时计算对话成本<br>- 支持多货币显示 | **多架构优化**<br>ARM64 原生支持：<br>- Apple Silicon 完美运行<br>- 树莓派 / Orange Pi 优化<br>- 减少内存占用<br>- 加快启动速度 |
| **模型权限管理**<br>灵活的访问控制：<br>- 批量设置模型可见性<br>- 公开 / 私有状态切换<br>- 按组分配模型权限 | **启动性能优化**<br>大幅提升加载速度：<br>- Lazy Loading 策略<br>- 智能缓存机制<br>- 精简 Docker 镜像<br>- 减少首屏等待时间 |

### 🎨 交互体验打磨

| | |
| :--- | :--- |
| **对话分支**<br>从任意消息创建 **Branch Chat**：<br>- 探索不同的对话走向<br>- 并排比较多个响应<br>- 侧边栏快速切换分支 | **上下文控制**<br>精准管理发送给模型的内容：<br>- 可视化插入 Context Break<br>- 自定义 Context Count<br>- 智能清除历史上下文 |
| **智能 Logo 匹配**<br>自动适配模型图标：<br>- 20+ LLM 提供商支持<br>- 模糊匹配算法<br>- GPT / Claude / Gemini / Qwen 等 | **深度中文优化**<br>全量汉化：<br>- 新增功能翻译<br>- 专业术语校对<br>- 报错信息本地化<br>- 符合中文习惯 |

---

## ⚙️ 推荐配置

启动 Open WebUI 后，建议进行以下配置以获得最佳体验：

| | |
| :--- | :--- |
| **1. 启用 Responses API**<br>在 **连接设置** 中开启 `Use Responses API`，即可：<br>- 体验 OpenAI 新版接口<br>- 查看模型思考过程<br>- 使用 o1/o3 推理模型 | **2. 配置 Gemini**<br>在 **Gemini 接口** 中填入 API Key：<br>- 使用原生 SDK 特性<br>- 支持 `thinking_budget`<br>- 原生工具调用 |
| **3. 开启计费显示**<br>在 **模型设置** 中配置费率：<br>- 设置输入/输出价格<br>- 启用计费显示<br>- 实时掌握成本 | **4. 启用对话分支**<br>在任意对话中使用 **分支功能**：<br>- 右键消息选择 "创建分支"<br>- 或使用快捷键<br>- 侧边栏管理分支 |

---

## 📊 与官方版本对比

| 特性 | 官方原版 | 本定制版 | 差异说明 |
|:-----|:--------:|:--------:|:---------|
| **API 协议** | Chat Completions | ✅ Responses API + Chat | 支持新版 API 及思考过程流式输出 |
| **Gemini 支持** | OpenAI 兼容层 | ✅ 原生 SDK | 完整支持原生参数与特性 |
| **推理控制** | 基础 | ✅ Reasoning Effort | 可调节推理强度 (Low/Med/High) |
| **对话分支** | 无 | ✅ Branch Chat | 支持分支创建与管理 |
| **上下文控制** | 基础 | ✅ Context Break | 可视化断点 + Context Count |
| **计费系统** | 无 | ✅ 完整计费 | 多模式、多货币、实时计算 |
| **运行环境** | 仅 x86_64 | ✅ x86_64 + ARM64 | 支持树莓派等 ARM 设备 |
| **本地化** | 社区翻译 | ✅ 深度校对 | 更准确的中文术语 |
| **启动速度** | 标准 | ✅ 优化 | Lazy Loading + 缓存策略 |

---

## 📝 最新更新 (v0.7.3-1)

### 修复

- 🔧 **Gemini API 工具调用全面修复**
  - 修复 functionResponse 角色格式错误
  - 添加 Gemini 3 缺少 thought_signature 时的兼容处理
  - 修复并行多工具调用时 index 冲突问题

### v0.7.3 主要更新

- 🌳 **对话分支功能** - 从任意消息创建分支，探索不同方向
- 🤖 **Responses API 支持** - 完整对接 OpenAI 新版接口
- 🧠 **自定义推理强度** - 精细控制 Reasoning Effort
- 🗑️ **智能上下文清除** - 轻量级实现，优化 Token 使用
- 🖼️ **图像编辑功能** - 界面内直接编辑图像
- 🎨 **智能 Logo 匹配** - 自动为 20+ 提供商适配图标
- 📦 **ARM64 支持** - 扩展部署灵活性

> 📋 查看 [完整更新日志](./CHANGELOG.md)

---

## 🔧 故障排除

### ARM 设备出现 "exec format error"

**问题**：在 ARM64 设备上运行出现 `exec /usr/bin/bash: exec format error`

**原因**：拉取了 x86_64 架构的镜像

**解决**：使用带 `-arm64` 后缀的镜像标签

```bash
# 错误的方式
docker pull ghcr.io/ztx888/openwebui:latest

# 正确的方式
docker pull ghcr.io/ztx888/openwebui:latest-arm64
```

### 如何判断设备架构？

```bash
# Linux / macOS
uname -m
# 输出 x86_64 = Intel/AMD
# 输出 aarch64 或 arm64 = ARM64

# Docker
docker info | grep Architecture
```

---

## 🙌 致谢与声明

本项目基于 [open-webui/open-webui](https://github.com/open-webui/open-webui) 开发，感谢原作者及社区的杰出贡献。

- **同步策略**：定期同步上游 `main` 分支，优先合并新特性
- **许可证**：遵循 [MIT License](./LICENSE)
- **问题反馈**：[GitHub Issues](https://github.com/ztx888/open-webui/issues)
- **讨论交流**：[GitHub Discussions](https://github.com/ztx888/open-webui/discussions)

---

<p align="center">
  <sub>Made with ❤️ for the AI community</sub>
  <br/>
  <sub>专注于更好的 AI 对话体验</sub>
</p>
