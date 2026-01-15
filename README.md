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
  <img src="https://img.shields.io/badge/Version-v0.7.4+-orange?style=for-the-badge&logo=git" alt="Version"/>
    <img src="https://img.shields.io/badge/Arch-x86__64%20%7C%20ARM64-blueviolet?style=for-the-badge&logo=docker" alt="Arch Badge"/>
</p>

---

## 💡 简介

本项目基于优秀的 [Open WebUI](https://github.com/open-webui/open-webui) 构建，旨在为特定需求场景提供**功能扩展**与**体验优化**。我们保持对上游的紧密跟随，并在此基础上增添了更精细的模型控制、更符合中文习惯的本地化以及一些便捷的实验性功能。

---

## ✨ 特色功能概览

### 🧠 模型能力深度集成

| 功能 | 详情 |
|------|------|
| **OpenAI Responses API** | ✅ **首发支持**：完整对接 OpenAI 新版 `/v1/responses` 接口，支持流式输出与 **Reasoning Content (思考过程)** 实时展示。 |
| **Google Gemini 原生** | 🔌 **直连官方**：内置 Gemini 原生 SDK，支持 `thinking_budget` 等特有参数，无需中间层转换。 |
| **Reasoning Effort** | 🎛️ **灵活控制**：支持为 o1/o3 等模型配置推理强度（Low/Medium/High），并支持自定义输入。 |
| **图像编辑优化** | 🖼️ **Token节省**：智能识别图像编辑上下文，自动精简历史消息，既保留图像又节省大量 Token。 |

### 🛠️ 系统与管理增强

| 功能 | 详情 |
|------|------|
| **精细化计费** | 💰 **运营级方案**：支持按次/Token计费，区分输入/输出/推理价格，实时计算对话成本。 |
| **ARM 架构支持** | 🍓 **多端运行**：提供 ARM64 镜像，完美运行于 Raspberry Pi 等设备。 |
| **模型权限管理** | 🔒 **访问控制**：支持设置模型的公开/私有状态，灵活分配资源。 |
| **启动速度优化** | 🚀 **性能提升**：Lazy Loading 策略 + 镜像精简，内存占用大幅降低，启动更迅速。 |

### 🎨 交互体验打磨

| 功能 | 详情 |
|------|------|
| **对话分支** | 🌿 **思维发散**：在任意对话节点创建新分支 (Branch Chat)，在同一标签页探索不同走向。 |
| **上下文控制** | ✂️ **精准断点**：可视化插入 Context Break，精准控制发送给模型的上下文长度；支持设置 Context Count。 |
| **品牌 Logo 适配** | 🏷️ **自动匹配**：智能模糊匹配算法，自动为各类模型（GPT, Claude, Gemini, Qwen 等）适配精美图标。 |
| **深度中文优化** | 🇨🇳 **全量汉化**：覆盖新增功能、专业术语、报错信息的深度本地化翻译。 |

---

## 🚀 快速开始

### Docker 一键部署

支持 x86_64 real ARM64 架构，自动拉取对应镜像。

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest
```

### 💡 推荐设置

1.  **启用 Responses API**: 在 Open WebUI 连接设置中开启 `Use Responses API`，即可体验新版接口与思考过程展示。
2.  **配置 Gemini**: 直接在 `Gemini 接口` 中填入 Key 即可使用原生功能。
3.  **开启计费显示**: 在模型设置中配置费率，即时掌握 Token 消耗。

---

## 📊 功能差异对比

| 特性 | 官方原版 | 本定制版 | 差异点 |
|:-----|:--------:|:--------:|:-------|
| **API 协议** | Chat Completions | **Responses API + Chat** | 支持新版 API 及思考过程流式输出 |
| **Gemini 支持** | OpenAI 兼容层 | **原生 SDK** | 支持更多原生参数与特性 |
| **推理控制** | 基础 | **Reasoning Effort** | 支持调节推理强度 |
| **计费系统** | 无 | **完整计费** | 支持多模式、多货币计费 |
| **对话管理** | 基础 | **分支 & 断点** | 更灵活的对话流控制 |
| **运行环境** | 通用 | **ARM & x86 优化** | 针对低功耗设备优化内存与构建 |
| **本地化** | 社区翻译 | **深度校对** | 更准确的中文术语 |

---

## 🙌 致谢与声明

本项目基于 [open-webui/open-webui](https://github.com/open-webui/open-webui) 开发，感谢原作者及社区的杰出工作。

- **同步策略**: 定期同步上游 `main` 分支，优先合并上游新特性。
- **许可证**: 遵循 [MIT License](./LICENSE)。

---

<p align="center">
  <sub>Made with ❤️ for the AI community</sub>
</p>
