# Open WebUI 👋

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tjbck)

![Open WebUI Banner](./banner.png)

<p align="center">
  <a href="README.md">English</a> ·
  <strong>中文</strong>
</p>

**Open WebUI 是一个[可扩展](https://docs.openwebui.com/features/extensibility/plugin)、功能丰富且用户友好的自托管 AI 平台，旨在完全离线运行。** 它支持 **Ollama** 和 **OpenAI 兼容的 API** 等多种 LLM 运行器，并内置了用于 RAG 的**推理引擎**，使其成为一个**强大的 AI 部署解决方案**。

对开源 AI 充满热情？[加入我们的团队 →](https://careers.openwebui.com/)

![Open WebUI Demo](./demo.png)

> [!TIP]  
> **正在寻找 [企业版方案](https://docs.openwebui.com/enterprise)？** – **[立即与我们的销售团队联系！](https://docs.openwebui.com/enterprise)**
>
> 获取**增强功能**，包括**自定义主题和品牌定制**、**服务水平协议 (SLA) 支持**、**长期支持 (LTS) 版本**等等！

如需更多信息，请务必查看我们的 [Open WebUI 文档](https://docs.openwebui.com/)。

## Open WebUI 核心功能 ⭐

- 🚀 **轻松设置**：使用 Docker 或 Kubernetes（kubectl、kustomize 或 helm）无缝安装，支持 `:ollama` 和 `:cuda` 标签镜像，提供无忧体验。

- 🤝 **Ollama/OpenAI API 集成**：轻松集成 OpenAI 兼容的 API，可与 Ollama 模型并排进行多样化对话。自定义 OpenAI API URL 以连接 **LMStudio、GroqCloud、Mistral、OpenRouter 等**。

- 🛡️ **细粒度的权限和用户组**：允许管理员创建详细的用户角色和权限，确保安全的用户环境。这种细粒度控制不仅增强了安全性，还允许定制化的用户体验。

- 📱 **响应式设计**：在台式机、笔记本电脑和移动设备上享受无缝体验。

- 📱 **移动端渐进式 Web 应用 (PWA)**：在移动设备上通过 PWA 享受类似原生应用的体验，提供 localhost 上的离线访问和无缝的用户界面。

- ✒️🔢 **完善的 Markdown 和 LaTeX 支持**：通过全面的 Markdown 和 LaTeX 能力提升您的 LLM 体验，实现更丰富的交互。

- 🎤📹 **免提语音/视频通话**：通过集成的免提语音和视频通话功能实现无缝沟通。支持多种语音转文本提供商（本地 Whisper、OpenAI、Deepgram、Azure）和文本转语音引擎（Azure、ElevenLabs、OpenAI、Transformers、WebAPI）。

- 🛠️ **模型构建器**：通过 Web UI 轻松创建 Ollama 模型。通过 [Open WebUI Community](https://openwebui.com/) 集成轻松创建和添加自定义角色/智能体、自定义聊天元素并导入模型。

- 🐍 **原生 Python 函数调用工具**：在工具工作区中使用内置代码编辑器支持增强您的 LLM。只需添加纯 Python 函数即可实现与 LLM 的无缝集成。

- 💾 **持久化 Artifact 存储**：内置用于 Artifact 的键值存储 API，支持日志、追踪器、排行榜和协作工具，跨会话提供个人和共享数据范围。

- 📚 **本地 RAG 集成**：支持多种向量数据库（共 9 种）和内容提取引擎（Tika、Docling、Document Intelligence、Mistral OCR、外部加载器）。直接将文档加载到聊天中或添加到文档库，在查询前使用 `#` 命令即可轻松访问。

- 🔍 **用于 RAG 的 Web 搜索**：使用包括 `SearXNG`、`Google PSE`、`Brave Search`、`Tavily`、`Perplexity`、`DuckDuckGo`、`Jina` 等在内的 15+ 个提供商执行 Web 搜索，并将结果直接注入聊天体验。

- 🌐 **网页浏览能力**：使用 `#` 命令后跟 URL，将网站无缝集成到您的聊天体验中。

- 🎨 **图像生成与编辑集成**：使用 OpenAI DALL-E、Gemini、ComfyUI（本地）和 AUTOMATIC1111（本地）等多种引擎创建和编辑图像。

- ⚙️ **多模型对话**：同时与多个模型进行交互，发挥它们各自的优势以获得最佳回复。

- 🔐 **基于角色的访问控制 (RBAC)**：通过受限权限确保安全访问；只有授权人员可以访问您的 Ollama，专属的模型创建/拉取权限保留给管理员。

- 🗄️ **灵活的数据库和存储选项**：支持 SQLite（带可选加密）、PostgreSQL，或配置云存储后端（S3、Google Cloud Storage、Azure Blob Storage）。

- 🔍 **高级向量数据库支持**：支持 ChromaDB、PGVector、Qdrant、Milvus、Elasticsearch 等 9 种向量数据库选项。

- 🔐 **企业级身份认证**：全面支持 LDAP/Active Directory 集成、SCIM 2.0 自动配置、SSO 以及 OAuth 提供商。

- ☁️ **云原生集成**：原生支持 Google Drive 和 OneDrive/SharePoint 文件选择。

- 📊 **生产级可观测性**：内置对追踪、指标和日志的 OpenTelemetry 支持。

- ⚖️ **水平扩展性**：支持基于 Redis 的会话管理和 WebSocket，适用于负载均衡器后的多工作节点部署。

- 🌐🌍 **多语言支持**：通过我们的国际化 (i18n) 支持，以您偏好的语言使用 Open WebUI。

- 🧩 **Pipelines，Open WebUI 插件支持**：使用 [Pipelines 插件框架](https://github.com/openwebui/pipelines) 无缝集成自定义逻辑和 Python 库。

- 🌟 **持续更新**：我们致力于通过定期的更新、修复和新功能不断改进 Open WebUI。

想要了解更多关于 Open WebUI 的功能？请查看我们的 [Open WebUI 文档](https://docs.openwebui.com/features) 以获取全面概览！

---

我们衷心感谢赞助商的慷慨支持。你们的贡献帮助我们维护和改进项目。谢谢！

## 如何安装 🚀

### 通过 Python pip 安装 🐍

可以使用 Python 包安装程序 pip 安装 Open WebUI。在开始之前，请确保您使用的是 **Python 3.11** 以避免兼容性问题。

1. **安装 Open WebUI**：
   打开终端并运行以下命令：

   ```bash
   pip install open-webui
   ```

2. **运行 Open WebUI**：
   安装完成后，执行以下命令启动：

   ```bash
   open-webui serve
   ```

启动后，您可以在浏览器中访问 `http://localhost:8080` 开启您的体验！

### 使用 Docker 运行 🐳

#### 若 Ollama 在您的计算机上
使用以下命令：

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
```

#### 若 Ollama 在远程服务器上
要连接到远程服务器上的 Ollama，请将 `OLLAMA_BASE_URL` 更改为服务器的 URL：

```bash
docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
```

#### 运行支持 Nvidia GPU 的 Open WebUI
使用以下命令：

```bash
docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:cuda
```

### 仅适用于 Open WebUI 的 Docker 镜像
如果您不打算使用 Ollama，请使用以下命令：

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
```

有关其他安装方法（如 Kubernetes、Caddy、Conda 等），请参考我们的 [官方文档](https://docs.openwebui.com/getting-started/)。

## 故障排除
遇到问题？请前往我们的 [GitHub Issues](https://github.com/open-webui/open-webui/issues) 或加入我们的 [Discord 社区](https://discord.gg/5rJgQTnV4s) 寻求帮助。

## 贡献 (Contributing)
欢迎参与贡献！请参阅我们的 [贡献指南](CONTRIBUTING.md) 以获取更多信息。

## 许可证 (License)
本项目采用 [MIT 许可证](LICENSE)。
