# Open WebUI (自定义增强版) 🚀

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
  <img src="https://img.shields.io/badge/Version-v0.7.3+-orange?style=for-the-badge&logo=git" alt="Version"/>
</p>

---

## ✨ 核心增强功能

本仓库是 [Open WebUI](https://github.com/open-webui/open-webui) 的深度定制版本，专为**提升中文体验**与**多模型管理效率**而打造。

---

### 🌐 Gemini API 原生集成

<img src="https://img.shields.io/badge/Google-Gemini-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>

不再依赖 OpenAI 兼容层，直接调用原生接口！

| 功能 | 说明 |
|------|------|
| 🔌 原生支持 | 完整对接 Google Gemini API |
| ⚙️ 独立入口 | 专属配置页面，与 OpenAI/Ollama 并列 |
| 📋 模型同步 | 自动同步最新 Gemini 模型列表 |
| 🎛️ 高级参数 | 支持 `thinking_budget` 等特有参数 |
| 🏷️ 标签分组 | 修复外部连接标签不显示的问题 |

---

### 💰 精细化计费系统

<img src="https://img.shields.io/badge/Billing-System-gold?style=flat-square" alt="Billing"/>

企业级、运营级的模型计费方案。

| 功能 | 说明 |
|------|------|
| 📊 多模式计费 | 支持 免费 / 按次 / 按Token 三种模式 |
| 💱 双货币支持 | 完美支持 CNY (¥) 和 USD ($) |
| 🔢 自定义倍率 | 可针对输入/输出分别设置价格倍率 |
| 💵 实时成本 | 聊天过程中自动计算并展示消耗金额 |

---

### 📊 智能用量统计

<img src="https://img.shields.io/badge/Usage-Statistics-purple?style=flat-square" alt="Stats"/>

让每一次对话的消耗都清晰可见。

| 功能 | 说明 |
|------|------|
| ✅ 默认开启 | 无需繁琐配置，开箱即用的 Usage 能力 |
| 📈 详细分类 | 区分 Input、Output 和 Reasoning Token |
| 🎨 美化展示 | 重新设计的 Token 统计 UI，直观易读 |
| 💰 费用计算 | 结合计费配置，自动计算单次对话成本 |

---

### 🔀 对话分支功能 <sup>NEW</sup>

<img src="https://img.shields.io/badge/Conversation-Branch-brightgreen?style=flat-square" alt="Branch"/>

从任意对话节点创建新分支，探索不同方向！

| 功能 | 说明 |
|------|------|
| 🌿 一键分支 | 在任意 AI 回复处点击分支按钮 |
| 📋 历史保留 | 完整保留从对话开始到该节点的所有内容 |
| 🚀 即时跳转 | 创建后自动跳转到新对话 |
| 💡 使用场景 | 想问多个问题但不想污染当前上下文时 |

**使用方法**: 鼠标悬停在 AI 回复上 → 点击 🔗 **分支按钮** → 自动创建新对话并跳转

---

### ⚡ 体验与性能优化

<img src="https://img.shields.io/badge/UX%20%26%20Perf-Turbo-orange?style=flat-square" alt="UX"/>

专注于流畅度与便捷性的深度打磨。

| 功能 | 说明 |
|------|------|
| 🎨 品牌图标 | 20+ LLM 品牌 Logo 自动匹配 (GPT/Claude/Gemini/Qwen...) |
| ⚡ 秒级加载 | 模型设置页启用智能缓存，**告别 3秒+ 等待** |
| 🚀 极速启动 | Slim 模式 + 懒加载，容器内存占用降低 40% |
| 🔧 快捷入口 | 模型选择器添加「模型设置」直达按钮 (管理员) |
| 🧠 推理增强 | 推理强度 (Reasoning Effort) 支持下拉与自定义输入 |
| 📐 上下文控制 | 支持设置发送给模型的历史消息条数 |

---

### 🇨🇳 深度中文本地化

<img src="https://img.shields.io/badge/I18n-简体中文-red?style=flat-square" alt="I18n"/>

更符合中文用户习惯的界面交互。

| 功能 | 说明 |
|------|------|
| 🌍 全界面汉化 | 覆盖所有新增功能与设置项 |
| 📝 四字标签 | 高级参数采用整齐划一的四字中文标签 |
| 📚 术语校准 | 计费、Token 等专业术语的精准翻译 |
| 🔄 持续更新 | 跟随上游版本实时更新本地化内容 |

---

### 🐳 自动化构建与部署

<img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue?style=flat-square&logo=github-actions" alt="CI/CD"/>

现代化的开发运维流程支持。

| 功能 | 说明 |
|------|------|
| 🔨 自动构建 | 随代码提交自动触发 Docker 镜像构建 |
| 📦 镜像托管 | 推送到 GHCR (GitHub Container Registry) |
| ⚙️ 架构优化 | 针对 x86_64 平台优化的精简构建 |
| 🏷️ 最新标签 | `ghcr.io/ztx888/openwebui:latest` |

---

## 🚀 快速部署

### Docker 一键启动

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest
```

### 💡 推荐配置

1. **配置 Gemini**: 进入 `管理设置` → `连接` → `Gemini 接口`，填入 API Key
2. **开启计费**: 进入 `模型设置`，为模型选择 `按Token` 计费并设置费率
3. **享受极速**: 点击模型选择器的 `⚙️` 图标，体验秒开的模型配置页

---

## 📋 功能对比

| 功能特性 | 官方上游 | 本定制版 | 核心优势 |
|:---------|:--------:|:--------:|:---------|
| **Gemini API** | ❌ 仅 OpenAI 兼容 | ✅ 原生 SDK | Thinking Parameters 支持 |
| **模型计费** | ❌ 无 | ✅ 多模式 | 运营必备，成本可控 |
| **Token 用量** | ⚠️ 基础 | ✅ 美化+分类 | 信息更全，展示更美 |
| **对话分支** | ❌ 无 | ✅ 一键分支 | 探索不同方向不污染上下文 |
| **模型页加载** | ⚠️ 远程 API | ✅ 智能缓存 | **瞬时响应** |
| **内存占用** | ⚠️ ~1.2GB | ✅ ~0.6GB | **省 40%+** |
| **中文本地化** | ⚠️ 基础 | ✅ 深度润色 | 界面更专业 |

---

## 🔄 同步与维护

本仓库定期与上游 [open-webui/open-webui](https://github.com/open-webui/open-webui) 的 `main` 分支同步。

- **合并策略**: 使用 `ours` 策略优先保留所有自定义功能
- **冲突处理**: 手动解决代码冲突，确保功能稳定性
- **功能跟进**: 上游发布新功能时，第一时间进行适配和汉化

---

## 📜 许可证

本项目遵循 [MIT License](./LICENSE)。
基于 [Open WebUI](https://github.com/open-webui/open-webui) 二次开发。
