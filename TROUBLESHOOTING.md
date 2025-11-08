# 本地开发故障排除

## 问题: "Open WebUI 需要后端服务" 错误

### 🔧 快速解决方案

**请在浏览器中进行硬刷新:**

- **macOS**: `Cmd + Shift + R` 
- **Windows/Linux**: `Ctrl + Shift + R`

然后检查是否解决问题。

### 📋 详细排查步骤

#### 1. 打开浏览器开发者工具

- **macOS**: `Cmd + Option + I`
- **Windows/Linux**: `F12`

#### 2. 检查 Console (控制台)

查找是否有错误消息,特别是:
- 红色的错误信息
- 网络请求失败
- CORS 相关错误

#### 3. 检查 Network (网络) 标签

1. 切换到 Network 标签
2. 刷新页面
3. 查找对 `http://localhost:8080/api/config` 的请求
4. 如果找到,点击查看:
   - **Status** 应该是 `200`
   - **Response** 应该包含 JSON 配置

#### 4. 清除本地存储

1. 在开发者工具中,转到 **Application** 标签
2. 左侧找到 **Local Storage**
3. 展开并点击 `http://localhost:5050`
4. 点击右键 → **Clear**
5. 刷新页面

### ✅ 验证服务状态

在终端运行:

```bash
# 测试后端 API
curl http://localhost:8080/api/config

# 检查端口占用
lsof -i :8080 -i :5050 | grep LISTEN
```

如果 curl 命令返回 JSON 配置,说明后端正常运行。

### 🔄 重启服务 (如果需要)

如果上述方法无效,停止当前服务 (`Ctrl + C`) 并重新启动:

**后端:**
```bash
cd backend
source venv/bin/activate
python -m uvicorn open_webui.main:app --reload --port 8080 --host 0.0.0.0
```

**前端:**
```bash
npm run dev:5050
```

### 🌐 尝试不同端口

如果端口冲突,可以使用不同端口:

**前端:**
```bash
npm run dev -- --port 3000
```

然后访问 `http://localhost:3000`

---

**还有问题?** 查看 `/Users/sylar/my_ws/open-webui-next/LOCAL_SETUP.md` 获取完整设置指南。
