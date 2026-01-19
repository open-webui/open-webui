# 🧠 Open WebUI v0.7.3-3 - Gemini 思考链支持 & Token 显示修复

这是一个功能增强版本，为 Gemini 3 系列模型添加了思考链支持，并修复了 Token 使用量显示问题。

---

## ✨ 新功能

### 🧠 **Gemini 思考链支持**
Gemini 3 系列模型现在支持显示思考过程！

- ✅ **支持模型：** gemini-3-flash-preview、gemini-3-pro-preview
- ✅ **自动启用：** 当设置 reasoning_effort 参数时，自动启用思考链
- ✅ **实时显示：** 思考过程会流式输出到前端界面
- ✅ **统一体验：** 与 DeepSeek 等模型的思考链体验保持一致

**使用方法：** 在模型设置中配置 reasoning_effort 参数（如 low/medium/high），即可看到模型的推理过程。

---

## 🔧 修复

### 📊 **Token 使用量显示**
- 修复了对话完成后 token 使用量不显示的问题
- 现在 prompt_tokens、completion_tokens、total_tokens 会正确显示
- 工具调用的 token 消耗也会被正确累加统计

### 🌊 **思考内容流式输出**
- 修复了 reasoning_content 未能流式发送到前端的问题
- 思考过程现在会实时显示，而非等待完成后一次性展示

---

## ⚡ 优化

### 🧹 **代码精简**
- 移除了不必要的中间流 usage 发送逻辑
- 清理了开发阶段的调试日志
- 简化了工具调用 token 累加逻辑

---

## 📦 升级指南

### Docker 用户
```bash
docker pull ghcr.io/open-webui/open-webui:main
docker restart open-webui
```

### Git 用户
```bash
git pull origin main
git checkout v0.7.3-3
npm install
npm run build
```

---

## 🔍 技术细节

### Gemini 思考链实现

#### thinkingConfig 配置
```python
gemini_payload["generationConfig"]["thinkingConfig"] = {
    "thinkingBudget": budget,  # 根据 reasoning_effort 映射
    "includeThoughts": True    # 必须设置为 True 才能获取思考内容
}
```

#### reasoning_effort 映射
| reasoning_effort | thinkingBudget |
|-----------------|----------------|
| low             | 1024           |
| medium          | 8192           |
| high            | 24576          |

#### 思考内容提取
Gemini API 返回的思考内容通过 `part.get("thought") is True` 标识，系统会自动提取并转换为 reasoning_content 格式。

### Token 使用量处理

#### 简化后的逻辑
- 只在最终 `done` 消息中包含 usage 信息
- 工具调用的 token 会累加到最终统计中
- 移除了中间流的 usage 发送，减少网络开销

---

## 🔗 相关链接

- 📋 [完整更新日志](https://github.com/open-webui/open-webui/blob/main/CHANGELOG.md)
- 🐛 [问题反馈](https://github.com/open-webui/open-webui/issues)
- 💬 [社区讨论](https://github.com/open-webui/open-webui/discussions)

---

## 📝 已知限制

### Gemini 思考链的特性
与 DeepSeek 等模型不同，Gemini 的思考过程是在内部完成后一次性返回的，而非实时流式输出。这是 Gemini API 的设计特性：

- **Gemini：** 内部完成思考 → 一次性返回思考摘要 → 流式输出回答
- **DeepSeek：** 实时流式输出思考过程 → 流式输出回答

因此，使用 Gemini 时，思考内容会在短时间内快速显示完毕，然后开始流式输出回答。

---

> 💡 **提示：** 如果您使用 Gemini 3 系列模型，现在可以通过设置 reasoning_effort 来查看模型的思考过程了！

**感谢所有反馈问题的用户！您的反馈让 Open WebUI 变得更好！** 🙏

---

**发布日期：** 2026年1月19日
**版本号：** v0.7.3-3
