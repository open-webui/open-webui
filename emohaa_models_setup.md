# Emohaa模型写死配置指南

本文档介绍了如何在Open WebUI后端中写死模型的几种方法。

## 方法一：环境变量配置（推荐）

在启动应用前设置以下环境变量：

```bash
# 设置默认模型（多个模型用逗号分隔）
export DEFAULT_MODELS="emohaa-chat-v1,emohaa-analysis-v1,emohaa-counselor-v1"

# 设置模型显示顺序
export MODEL_ORDER_LIST='["emohaa-chat-v1", "emohaa-analysis-v1", "emohaa-counselor-v1"]'
```

或者在Docker中：

```bash
docker run -d \
  -e DEFAULT_MODELS="emohaa-chat-v1,emohaa-analysis-v1" \
  -e MODEL_ORDER_LIST='["emohaa-chat-v1", "emohaa-analysis-v1"]' \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  your-image-name
```

## 方法二：数据库预设模型（已实现）

当应用启动时，会自动向数据库插入以下预设模型：

### 1. Emohaa共情陪伴模型 (emohaa-chat-v1)
- **功能**：提供温暖的情感支持和陪伴
- **特点**：深度共情、耐心倾听、情感引导
- **适用场景**：日常聊天、情感支持、心理陪伴

### 2. Emohaa情绪分析模型 (emohaa-analysis-v1)  
- **功能**：专业的情绪识别和心理状态分析
- **特点**：客观分析、专业建议、数据支持
- **适用场景**：情绪分析、心理评估、专业咨询

### 3. Emohaa心理咨询师 (emohaa-counselor-v1)
- **功能**：模拟专业心理咨询师服务
- **特点**：专业咨询技巧、伦理意识、危机处理
- **适用场景**：心理咨询、心理健康支持、专业指导

## 方法三：运行时硬编码模型

通过修改 `backend/open_webui/utils/models.py` 中的 `HARDCODED_MODELS` 列表，可以添加运行时模型：

```python
HARDCODED_MODELS = [
    {
        "id": "your-custom-model",
        "name": "您的自定义模型",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "your-org",
        "meta": {
            "profile_image_url": "/favicon.png",
            "description": "您的模型描述",
            "capabilities": {
                "vision": False,
                "file_upload": True,
                "web_search": False,
                "image_generation": False,
                "code_interpreter": False,
                "citations": False,
            }
        },
        "params": {
            "system": "您的系统提示词"
        },
        "tags": [{"name": "标签1"}, {"name": "标签2"}],
    }
]
```

## 启动验证

启动应用后，查看日志应该会看到类似信息：

```
INFO: Initializing preset models...
INFO: ✅ 预设模型已创建: Emohaa共情陪伴模型 (ID: emohaa-chat-v1)
INFO: ✅ 预设模型已创建: Emohaa情绪分析模型 (ID: emohaa-analysis-v1)  
INFO: ✅ 预设模型已创建: Emohaa心理咨询师 (ID: emohaa-counselor-v1)
```

如果模型已存在，会看到：
```
INFO: ⚠️  预设模型已存在，跳过: emohaa-chat-v1
```

## 模型管理

- **查看模型**：管理员可以在 Admin Panel > Models 中查看所有预设模型
- **编辑模型**：可以修改模型的系统提示词、能力配置等
- **权限控制**：可以设置模型的访问权限，控制哪些用户可以使用

## 注意事项

1. **数据库备份**：预设模型会存储在数据库中，请确保定期备份
2. **版本管理**：建议使用版本号命名模型（如 v1, v2），便于后续升级
3. **性能影响**：预设模型会在每次启动时检查，对启动时间影响很小
4. **权限设置**：预设模型默认为公开访问，可根据需要调整权限

## 故障排除

如果预设模型没有正常创建：

1. 检查数据库连接是否正常
2. 查看应用启动日志中的错误信息
3. 确认管理员用户是否存在
4. 检查模型ID是否符合命名规范（不包含特殊字符）

## 自定义扩展

您可以根据需要修改预设模型配置，添加更多专门的Emohaa模型变体，如：
- 儿童心理支持模型
- 职场压力管理模型  
- 学习焦虑辅导模型
- 家庭关系咨询模型

每个模型都可以有专门的系统提示词和能力配置，以适应不同的使用场景。 