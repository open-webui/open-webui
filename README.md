# Open WebUI (Custom Edition)

<div align="center">
  <img src="./banner.png" alt="Open WebUI Banner" width="100%" />

  <br/>

  <a href="https://github.com/ztx888/open-webui">
    <img src="https://img.shields.io/badge/Fork-ztx888%2Fopen--webui-blue?style=for-the-badge&logo=github" alt="Fork Badge"/>
  </a>
  <a href="https://github.com/open-webui/open-webui">
    <img src="https://img.shields.io/badge/Upstream-open--webui-green?style=for-the-badge&logo=github" alt="Upstream Badge"/>
  </a>
  <img src="https://img.shields.io/badge/Version-v0.7.3--3-orange?style=for-the-badge&logo=git" alt="Version"/>
  <img src="https://img.shields.io/badge/Arch-x86__64%20%7C%20ARM64-blueviolet?style=for-the-badge&logo=docker" alt="Arch Badge"/>

  <br/><br/>
  <h3>功能增强 · 深度汉化 · 多架构支持</h3>
  <p>基于 Open WebUI 构建，提供更强的模型集成、精细的运营控制及流畅的中文体验。</p>
</div>

---

## 📖 简介

本项目紧密跟随上游更新，旨在解决官方版本在特定场景下的痛点。我们持续增添实用的扩展功能，让本地 AI 部署更加得心应手。

| 您的需求 / 痛点 | 本版本解决方案 |
| :--- | :--- |
| **想用 OpenAI 新版 Responses API？** | ✅ **首发支持**：完整兼容 `/v1/responses`，实时流式展示思考过程。 |
| **Gemini 丢失原生特性？** | ✅ **原生直连**：基于官方 SDK 开发，支持 `thinking_budget` 及原生工具调用。 |
| **需要精确控制 Token 成本？** | ✅ **精细计费**：支持按次/Token 计费，区分输入输出价格，实时统计。 |
| **设备是树莓派或 ARM 服务器？** | ✅ **多架构支持**：提供专门优化的 ARM64 镜像，拒绝 `exec format error`。 |
| **觉得机翻界面很难受？** | ✅ **深度汉化**：全量人工校对，专业术语更准确，报错信息更友好。 |

---

## 🚀 快速开始

### 🐳 Docker 一键部署

#### 1. x86_64 架构 (Intel/AMD)
适用于大多数 PC、服务器及云主机：

```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest
```

#### 2. ARM64 架构 (Apple Silicon / 树莓派 / 飞牛 NAS)
> ⚠️ **重要提示**：ARM64 设备请务必使用 `-arm64` 后缀的镜像标签！

```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest-arm64
```

#### 3. Docker Compose (推荐)

创建 `docker-compose.yml` 文件：

```yaml
services:
  open-webui:
    # ARM64 设备请改为: ghcr.io/ztx888/openwebui:latest-arm64
    image: ghcr.io/ztx888/openwebui:latest
    container_name: open-webui
    ports:
      - "3000:8080"
    volumes:
      - open-webui:/app/backend/data
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always

volumes:
  open-webui: {}
```
启动服务：`docker compose up -d`

---

## ✨ 核心特性

### 🧠 模型能力深度集成

我们重构了核心模型接口，确保你不必在“兼容性”和“新特性”之间做选择。

* **OpenAI Responses API 首发支持**
    * 完整支持 OpenAI 新版 `/v1/responses` 接口。
    * **流式思考**：实时展示 o1、o3 等推理模型的 Thinking Process (Reasoning Content)。
    * **推理步骤可视化**：让黑盒模型变得透明。

* **Google Gemini 原生 SDK**
    * 摒弃中间层转换，直连 Google 官方 SDK。
    * **原生参数**：完美支持 `thinking_budget` 等独有参数。
    * **全版本兼容**：完美适配 Gemini 2.5 Pro / Gemini 3。
    * **Function Calling**：支持原生的工具调用能力。

* **推理强度控制 (Reasoning Effort)**
    * 为 o1/o3 等模型提供 **Low / Medium / High** 三档预设。
    * 支持自定义数值输入，灵活平衡响应速度与生成质量。

* **智能图像编辑优化**
    * 优化的上下文管理逻辑，自动精简历史消息。
    * 只保留必要的图像引用，大幅节省 Token 消耗。

<br/>

### 🛠️ 系统管理增强

专为运营者和极客设计的高级管理功能。

* **精细化计费系统**
    * **运营级风控**：支持“按次计费”或“按 Token 计费”。
    * **差异化定价**：可分别设置输入、输出、推理的价格。
    * **实时成本**：对话界面实时显示预估消耗，支持多货币显示。

* **多架构原生优化**
    * **ARM64 专属构建**：Apple Silicon、树莓派 4/5、Orange Pi、飞牛 NAS 完美运行。
    * **性能调优**：针对低功耗设备优化内存占用与启动速度。

* **启动性能飙升**
    * 引入 Lazy Loading 策略与智能缓存机制。
    * 精简 Docker 镜像体积，显著减少首屏加载等待时间。

* **灵活的权限控制**
    * 支持批量设置模型的可见性（公开/私有）。
    * 按用户组分配模型权限，管理更加轻松。

<br/>

### 🎨 交互体验打磨

细节决定成败，我们优化了大量 UI/UX 细节。

* **对话分支 (Branch Chat)**
    * 从任意消息创建分支，平行探索不同的对话走向。
    * 支持侧边栏快速切换分支，并排比较多个模型的响应。

* **上下文精准控制**
    * **可视化截断**：支持可视化插入 Context Break。
    * **自定义长度**：自由设置 Context Count。
    * **历史清理**：一键智能清除无用的历史上下文。

* **智能 Logo 匹配**
    * 内置 20+ LLM 提供商图标支持。
    * 采用模糊匹配算法，自动为 GPT / Claude / Gemini / Qwen 等模型适配图标。

* **深度中文优化**
    * 全界面汉化，包括新增功能与报错信息。
    * 修正机器翻译的生硬术语，更符合中文语境与习惯。

---

## ⚙️ 推荐配置

启动 Open WebUI 后，建议按以下步骤配置以获得最佳体验（Best Practice）：

> **1. 启用 Responses API**
> 进入 **连接设置**，开启 `Use Responses API` 选项。
> * 效果：解锁 OpenAI o1/o3 系列模型的流式思考过程。

> **2. 配置 Gemini API**
> 进入 **Gemini 接口**，直接填入 API Key。
> * 效果：启用原生 SDK 模式，支持 Thinking Budget 和工具调用。

> **3. 开启计费显示 (可选)**
> 进入 **模型设置**，配置输入/输出费率并开启显示。
> * 效果：在对话框上方实时掌握 Token 成本。

> **4. 体验对话分支**
> 在任意对话气泡上右键，选择 **“创建分支”**。
> * 效果：不影响原对话流，开启新的探索路径。

---

## 📊 与官方版本对比

| 特性 | 官方原版 (Upstream) | 本定制版 (Custom) | 差异核心 |
| :--- | :---: | :---: | :--- |
| **API 协议** | Chat Completions | ✅ **Responses API + Chat** | 支持新版流式思考输出 |
| **Gemini 支持** | OpenAI 兼容层 | ✅ **原生 SDK** | 完整支持原生参数与工具 |
| **推理控制** | 基础 | ✅ **Reasoning Effort** | 可调节推理强度 |
| **对话分支** | 无 | ✅ **Branch Chat** | 支持多线性对话管理 |
| **上下文控制** | 基础 | ✅ **可视化断点** | 更强的 Token 掌控力 |
| **运行环境** | 仅 x86_64 | ✅ **x86_64 + ARM64** | 完美支持树莓派/NAS |
| **本地化** | 社区翻译 | ✅ **精修汉化** | 拒绝机翻感 |

---

## 📝 最新更新 (v0.7.3-3)

### 🚀 v0.7.3 重点功能
* 🌳 **对话分支功能**：从任意消息节点分叉，探索不同可能性。
* 🤖 **Responses API**：完整对接 OpenAI 新接口，展示推理链。
* 🧠 **自定义推理强度**：手动控制 o1/o3 的思考预算。
* 🗑️ **智能上下文清除**：轻量化实现，更方便地管理 Token。
* 🎨 **智能 Logo 系统**：自动适配 20+ 厂商的模型图标。

### 🐛 修复与优化
* **Gemini API**：修复了 `functionResponse` 角色格式错误及多工具并行调用的冲突。
* **兼容性**：增加了对 Gemini 3 缺少 `thought_signature` 字段的容错处理。

> 📋 查看 [完整更新日志](./CHANGELOG.md)

---

## 🔧 常见问题 (FAQ)

<details>
<summary><strong>Q: 运行出现 "exec format error" 报错？</strong></summary>
<br>
这是因为您在 ARM 设备（如树莓派、M1/M2 Mac）上拉取了 x86 镜像。<br>
<strong>解决方法</strong>：请使用带 -arm64 后缀的镜像：
<pre>docker pull ghcr.io/ztx888/openwebui:latest-arm64</pre>
</details>

<details>
<summary><strong>Q: 镜像标签该选哪个？</strong></summary>
<br>
<ul>
    <li><code>latest</code>：适用于 Intel/AMD CPU（常规 PC、服务器）。</li>
    <li><code>latest-arm64</code>：适用于 Apple Silicon、树莓派、飞牛 NAS 等 ARM 设备。</li>
</ul>
</details>

---

## 🙌 致谢与声明

本项目基于 [open-webui/open-webui](https://github.com/open-webui/open-webui) 开发，感谢原作者及社区的杰出贡献。

* **同步策略**：定期同步上游 `main` 分支，优先合并新特性。
* **许可证**：遵循 [MIT License](./LICENSE)。
* **反馈**：欢迎提交 [Issues](https://github.com/ztx888/open-webui/issues) 或加入 [Discussions](https://github.com/ztx888/open-webui/discussions)。

<br/>

<p align="center">
  <sub>Made with ❤️ for the AI community</sub>
  <br/>
  <sub>专注于更好的 AI 对话体验</sub>
</p>
