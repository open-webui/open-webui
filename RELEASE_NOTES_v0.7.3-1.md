# 🔧 Open WebUI v0.7.3-1 - Gemini API 工具调用修复补丁

这是一个紧急修复版本，专门解决 Gemini 模型在使用工具调用功能时遇到的关键问题。

---

## ✨ 主要修复

### 🤖 **Gemini API 工具调用全面修复**
修复了 Gemini 2.5-pro 和 Gemini 3 模型在使用工具调用（如网页搜索）时返回 400 错误的严重问题：

- ✅ **修复 functionResponse 角色格式错误** - 解决了与 Gemini API 的兼容性问题
- ✅ **Gemini 3 兼容性增强** - 添加了对缺少 thought_signature 字段的兼容处理
- ✅ **并行工具调用修复** - 修复了多工具并行调用时 index 冲突导致的参数合并问题

**影响范围：** 所有使用 Gemini 模型并启用工具调用功能的用户将受益于此修复。

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
git checkout v0.7.3-1
npm install
npm run build
```

---

## 🔗 相关链接

- 📋 [完整更新日志](https://github.com/open-webui/open-webui/blob/main/CHANGELOG.md)
- 🐛 [问题反馈](https://github.com/open-webui/open-webui/issues)
- 💬 [社区讨论](https://github.com/open-webui/open-webui/discussions)

---

## 📝 下午更新总结

今天下午的工作聚焦于 Gemini API 的稳定性改进：

1. **问题排查** - 定位了 Gemini 工具调用失败的根本原因
2. **多层修复** - 从角色格式、兼容性处理到并行调用三个层面进行修复
3. **测试验证** - 确保修复在 Gemini 2.5-pro 和 Gemini 3 上都能正常工作
4. **版本发布** - 快速打包发布修复补丁，确保用户能及时获得更新

---

## 🔍 技术细节

### 修复的核心问题

#### 1. functionResponse 角色格式问题
**问题：** Gemini API 对工具调用响应的格式要求严格，之前的实现未正确处理 `functionResponse` 角色。
**解决：** 规范化了 functionResponse 的格式，确保与 Gemini API 规范完全兼容。

#### 2. Gemini 3 thought_signature 兼容性
**问题：** Gemini 3 模型在某些情况下不返回 `thought_signature` 字段，导致解析失败。
**解决：** 添加了容错处理，当该字段缺失时使用默认值或跳过处理。

#### 3. 并行工具调用 index 冲突
**问题：** 当同时调用多个工具时，index 参数冲突导致参数错误合并。
**解决：** 重构了并行调用逻辑，为每个工具调用分配独立的 index，避免冲突。

---

> 💡 **提示：** 如果您在使用 Gemini 模型时遇到工具调用问题，请立即升级到此版本！

**感谢所有反馈问题的用户！您的反馈让 Open WebUI 变得更好！** 🙏

---

**发布日期：** 2026年1月18日
**版本号：** v0.7.3-1
**提交哈希：** 31dbd3af6
