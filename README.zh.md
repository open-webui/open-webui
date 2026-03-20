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

- 🔍 **用于 RAG 的 Web 搜索**：使用包括 `SearXNG`、`Google PSE`、`Brave Search`、`Tavily`、`Perplexity`、`DuckDuckGo`、`Jina` 等在内的多个提供商执行 Web 搜索，并将结果直接注入聊天体验。

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

- 🌐🌍 **多语言支持**：通过我们的国际化 (i18n) 支持，以您偏好的语言使用 Open WebUI。欢迎加入我们扩展支持的语言！我们正积极寻求贡献者！

- 🧩 **Pipelines，Open WebUI 插件支持**：使用 [Pipelines 插件框架](https://github.com/openwebui/pipelines) 无缝集成自定义逻辑和 Python 库。启动您的 Pipelines 实例，将 OpenAI URL 设置为 Pipelines URL，即可探索无限可能。[示例](https://github.com/openwebui/pipelines/tree/main/examples) 包括**函数调用**、用于控制访问的**用户速率限制**、使用 Langfuse 等工具的**使用情况监控**、用于多语言支持的 **LibreTranslate 实时翻译**、**毒性消息过滤**等等。

- 🌟 **持续更新**：我们致力于通过定期的更新、修复和新功能不断改进 Open WebUI。

想要了解更多关于 Open WebUI 的功能？请查看我们的 [Open WebUI 文档](https://docs.openwebui.com/features) 以获取全面概览！

---

我们衷心感谢赞助商的慷慨支持。你们的贡献帮助我们维护和改进项目，确保我们能够继续为社区提供优质成果。谢谢！

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

这将启动 Open WebUI 服务器，您可以通过 [http://localhost:8080](http://localhost:8080) 进行访问。

### 使用 Docker 快速开始 🐳

> [!NOTE]  
> 请注意，对于某些 Docker 环境，可能需要额外的配置。如果您遇到任何连接问题，我们的 [Open WebUI 文档](https://docs.openwebui.com/) 中的详细指南随时准备为您提供帮助。

> [!WARNING]
> 使用 Docker 安装 Open WebUI 时，请务必在 Docker 命令中包含 `-v open-webui:/app/backend/data`。这一步至关重要，因为它确保了您的数据库已正确挂载，防止任何数据丢失。

> [!TIP]  
> 如果您希望在包含 Ollama 或 CUDA 加速的情况下使用 Open WebUI，我们建议使用带有 `:cuda` 或 `:ollama` 标签的官方镜像。要启用 CUDA，您必须在 Linux/WSL 系统上安装 [Nvidia CUDA 容器工具包](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/)。

### 使用默认配置安装

- **如果 Ollama 在您的计算机上**，请使用此命令：

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **如果 Ollama 在不同的服务器上**，请使用此命令：

  要连接到另一台服务器上的 Ollama，请将 `OLLAMA_BASE_URL` 更改为服务器的 URL：

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **要运行支持 Nvidia GPU 的 Open WebUI**，请使用此命令：

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
  ```

### 仅针对 OpenAI API 使用的安装

- **如果您仅使用 OpenAI API**，请使用此命令：

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

### 安装带有内置 Ollama 支持的 Open WebUI

这种安装方法使用一个将 Open WebUI 与 Ollama 捆绑在一起的单一容器镜像，从而可以通过单个命令进行简化设置。根据您的硬件设置选择适当的命令：

- **支持 GPU**：
  通过运行以下命令利用 GPU 资源：

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

- **仅限 CPU**：
  如果您不使用 GPU，请改用此命令：

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

这两个命令都可以实现 Open WebUI 和 Ollama 的内置、无忧安装，确保您可以迅速启动并运行一切。

安装完成后，您可以通过 [http://localhost:3000](http://localhost:3000) 访问 Open WebUI。尽情享受吧！ 😄

### 其他安装方法

我们提供各种安装替代方案，包括非 Docker 原生安装方法、Docker Compose、Kustomize 和 Helm。访问我们的 [Open WebUI 文档](https://docs.openwebui.com/getting-started/) 或加入我们的 [Discord 社区](https://discord.gg/5rJgQTnV4s) 获取全面指导。

有关设置本地开发环境的说明，请查看 [本地开发指南](https://docs.openwebui.com/getting-started/development)。

### 故障排除

遇到连接问题？我们的 [Open WebUI 故障排除文档](https://docs.openwebui.com/troubleshooting/) 可以为您提供帮助。如需进一步协助并加入我们的活力社区，请访问 [Open WebUI Discord](https://discord.gg/5rJgQTnV4s)。

#### Open WebUI：服务器连接错误

如果您遇到连接问题，通常是因为 WebUI Docker 容器无法访问容器内部的 Ollama 服务器（地址为 127.0.0.1:11434 或 host.docker.internal:11434）。在 Docker 命令中使用 `--network=host` 标志来解决此问题。请注意，端口会从 3000 变为 8080，访问链接为：`http://localhost:8080`。

**示例 Docker 命令**：

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### 保持您的 Docker 安装为最新版本

查看我们的 [Open WebUI 文档](https://docs.openwebui.com/getting-started/updating) 中的更新指南。

### 使用开发 (Dev) 分支 🌙

> [!WARNING]
> `:dev` 分支包含最新的不稳定功能和更改。使用该分支需自担风险，因为它可能包含错误或不完整的功能。

如果您想尝试最新的前沿功能并可以接受偶尔的不稳定性，可以像这样使用 `:dev` 标签：

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui --add-host=host.docker.internal:host-gateway --restart always ghcr.io/open-webui/open-webui:dev
```

### 离线模式

如果您在离线环境中运行 Open WebUI，可以将 `HF_HUB_OFFLINE` 环境变量设置为 `1`，以防止尝试从互联网下载模型。

```bash
export HF_HUB_OFFLINE=1
```

## 接下来要做什么？ 🌟

在 [Open WebUI 文档](https://docs.openwebui.com/roadmap/) 中发现我们路线图上的即将推出的功能。

## 许可证 📜

本项目包含多个许可证下的代码。当前代码库包括根据 Open WebUI 许可证许可的组件，并额外要求保留 "Open WebUI" 品牌，以及根据其各自原始许可证许可的先前贡献。有关许可证更改和代码各部分适用条款的详细记录，请参阅 [LICENSE_HISTORY](./LICENSE_HISTORY)。有关完整且更新的许可详情，请参阅 [LICENSE](./LICENSE) 和 [LICENSE_HISTORY](./LICENSE_HISTORY) 文件。

## 支持 💬

如果您有任何疑问、建议或需要帮助，请提交 issue 或加入我们的 [Open WebUI Discord 社区](https://discord.gg/5rJgQTnV4s) 与我们联系！ 🤝

## 星标历史 (Star History)

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

由 [Timothy Jaeryang Baek](https://github.com/tjbck) 创建 - 让我们一起让 Open WebUI 变得更加精彩！ 💪
