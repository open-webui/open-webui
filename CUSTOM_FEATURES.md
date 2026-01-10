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
</p>

---

## ✨ 自定义增强功能

本仓库是 [Open WebUI](https://github.com/open-webui/open-webui) 的个人定制版本，在保持与上游同步的同时，添加了以下增强功能：

<table>
<tr>
<td width="50%" valign="top">

### 🌐 Gemini API 原生集成

<img src="https://img.shields.io/badge/Google-Gemini-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>

- ✅ 原生支持 Google Gemini API
- ✅ 独立配置页面，与 OpenAI/Ollama 并列
- ✅ 完整的模型列表获取与管理
- ✅ 支持 Gemini 特有参数 (如 `thinking_budget`)

</td>
<td width="50%" valign="top">

### 💰 模型计费设置

<img src="https://img.shields.io/badge/Billing-CNY%20%7C%20USD-gold?style=flat-square" alt="Billing"/>

- ✅ 三种计费模式：免费 / 按次 / 按Token
- ✅ 支持 CNY (¥) 和 USD ($) 双货币
- ✅ 可配置输入/输出价格与倍率
- ✅ 聊天时自动计算并显示消耗成本

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📊 智能用量统计

<img src="https://img.shields.io/badge/Usage-Statistics-purple?style=flat-square" alt="Stats"/>

- ✅ 默认启用 Usage 能力
- ✅ 美化的 Token 用量展示
- ✅ 输入/输出/推理 Token 分类统计
- ✅ 根据计费配置自动计算费用

</td>
<td width="50%" valign="top">

### ⚡ 快捷入口与 UI 优化

<img src="https://img.shields.io/badge/UX-Enhanced-orange?style=flat-square" alt="UX"/>

- ✅ 模型选择器添加「模型设置」快捷入口
- ✅ 仅管理员可见，一键跳转编辑
- ✅ 模型头像缓存优化，提升加载速度
- ✅ 推理强度下拉选择 (支持自定义输入)

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🇨🇳 中文本地化增强

<img src="https://img.shields.io/badge/I18n-简体中文-red?style=flat-square" alt="I18n"/>

- ✅ 完整的简体中文界面
- ✅ 高级参数中文标签 (四字格式)
- ✅ 计费相关术语翻译
- ✅ 用量统计标签本地化

</td>
<td width="50%" valign="top">

### 🐳 自动化部署

<img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue?style=flat-square&logo=github-actions" alt="CI/CD"/>

- ✅ 自动构建 Docker 镜像
- ✅ 推送到 GHCR (GitHub Container Registry)
- ✅ 针对 x86_64 优化的单平台构建
- ✅ 标签: `ghcr.io/ztx888/openwebui:latest`

</td>
</tr>
</table>

---

## 🚀 快速开始

### Docker 部署

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/ztx888/openwebui:latest
```

### 配置 Gemini API

1. 进入 **管理设置** → **连接**
2. 点击 **Gemini 接口** 选项卡
3. 输入你的 Google API Key
4. 保存并刷新模型列表

---

## 📋 与上游的差异

| 功能 | 上游 | 本仓库 |
|------|------|--------|
| Gemini API | ❌ 不支持 | ✅ 原生支持 |
| 模型计费 | ❌ 无 | ✅ 多模式计费 |
| Usage 默认值 | `undefined` | `true` |
| 模型设置快捷入口 | ❌ 无 | ✅ 管理员可用 |
| 中文高级参数标签 | 英文 | 四字中文 |

---

## 🔄 同步策略

本仓库定期与上游 [open-webui/open-webui](https://github.com/open-webui/open-webui) 同步，合并时会：

- ✅ 保留所有自定义功能
- ✅ 采纳上游的新特性与修复
- ✅ 手动解决冲突，确保兼容性

---

## 📜 许可证

本项目继承 [Open WebUI](https://github.com/open-webui/open-webui) 的许可证。详细信息请参阅 [LICENSE](./LICENSE)。

---

<p align="center">
  <sub>基于 <a href="https://github.com/open-webui/open-webui">Open WebUI</a> 构建 | 由 <a href="https://github.com/ztx888">ztx888</a> 定制</sub>
</p>
