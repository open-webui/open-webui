# Emohaa Open WebUI

[English](docs/README.md) | [简体中文](docs/README.md)

---

📚 **完整文档请查看 [docs](./docs/) 目录**

## 快速开始

### 方法一：直接部署（推荐）
```bash
git clone https://github.com/gaivrt/emohaa-open-webui.git
cd emohaa-open-webui
chmod +x run-compose.sh
./run-compose.sh
```

### 方法二：导出镜像部署
```bash
# 本地构建并导出
./export_image.sh

# 传输到服务器
scp emohaa-open-webui.tar.gz user@server:/path/

# 服务器部署
docker load < emohaa-open-webui.tar.gz
./run_docker.sh
```

## 文档目录

- [📖 完整部署指南](./docs/DEPLOYMENT.md)
- [⚙️ 安装说明](./docs/INSTALLATION.md)
- [🛠️ 故障排除](./docs/TROUBLESHOOTING.md)
- [🔧 自定义指南](./docs/CUSTOMIZATION_CHECKLIST.md)
- [🤝 贡献指南](./docs/CONTRIBUTING.md)
- [🔒 安全说明](./docs/SECURITY.md)

## 支持

遇到问题？查看 [故障排除文档](./docs/TROUBLESHOOTING.md) 或提交 [Issue](https://github.com/gaivrt/emohaa-open-webui/issues)。

---

> 基于 [Open WebUI](https://github.com/open-webui/open-webui) 定制