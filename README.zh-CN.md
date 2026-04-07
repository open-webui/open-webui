# Open WebUI 👋

[English](./README.md) | [简体中文](./README.zh-CN.md)

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

**Open WebUI 是一个[可扩展](https://docs.openwebui.com/features/extensibility/plugin)、功能丰富且易于使用的自托管 AI 平台，专为完全离线运行而设计。** 它支持 **Ollama**、**兼容 OpenAI 的 API** 等多种大语言模型运行方式，并内置用于 RAG 的推理引擎，是一套**强大的 AI 部署解决方案**。

热爱开源 AI？[加入我们的团队 →](https://careers.openwebui.com/)

![Open WebUI Demo](./demo.png)

> [!TIP]
> **在寻找[企业版方案](https://docs.openwebui.com/enterprise)？** 立即[联系销售团队！](https://docs.openwebui.com/enterprise)
>
> 获取**增强能力**，包括**自定义主题与品牌化**、**SLA 支持**、**长期支持（LTS）版本**等更多特性。

更多信息请查看 [Open WebUI 官方文档](https://docs.openwebui.com/)。

## Open WebUI 的核心特性 ⭐

- 🚀 **轻松部署**：支持 Docker 或 Kubernetes（`kubectl`、`kustomize`、`helm`）一键安装，提供 `:ollama` 与 `:cuda` 标签镜像，部署体验顺畅无负担。

- 🤝 **Ollama / OpenAI API 集成**：除 Ollama 模型外，也可轻松接入兼容 OpenAI 的 API。你可以自定义 OpenAI API 地址，对接 **LMStudio、GroqCloud、Mistral、OpenRouter** 等服务。

- 🛡️ **细粒度权限与用户组管理**：管理员可创建详细的角色与权限策略，既提升安全性，也能为不同用户提供定制化体验。

- 📱 **响应式设计**：在台式机、笔记本和移动设备上都能获得一致流畅的使用体验。

- 📱 **移动端渐进式 Web 应用（PWA）**：提供接近原生应用的移动端体验，支持 localhost 离线访问，并拥有顺滑统一的界面。

- ✒️🔢 **完整支持 Markdown 与 LaTeX**：让大模型交互具备更强的表达能力，轻松处理富文本与公式内容。

- 🎤📹 **免手持语音 / 视频通话**：集成本地 Whisper、OpenAI、Deepgram、Azure 等多种语音转文本方案，以及 Azure、ElevenLabs、OpenAI、Transformers、WebAPI 等文本转语音引擎，打造更自然的交互式对话环境。

- 🛠️ **模型构建器**：可直接通过 Web 界面创建 Ollama 模型，添加自定义角色 / 智能体，自定义聊天元素，并通过 [Open WebUI Community](https://openwebui.com/) 轻松导入模型。

- 🐍 **原生 Python 函数调用工具**：工具工作区内置代码编辑器支持。只需添加纯 Python 函数即可实现 BYOF（Bring Your Own Function），让大模型无缝调用自定义能力。

- 💾 **持久化 Artifact 存储**：内置键值存储 API，可用于日志、追踪器、排行榜、协作工具等场景，并支持个人 / 共享两种数据作用域，跨会话持续保留。

- 📚 **本地 RAG 集成**：支持 9 种向量数据库和多种内容提取引擎（Tika、Docling、Document Intelligence、Mistral OCR、外部加载器），将文档直接加载进聊天或加入文档库，并通过 `#` 命令在提问前调用。

- 🔍 **RAG 联网搜索**：支持 `SearXNG`、`Google PSE`、`Brave Search`、`Kagi`、`Mojeek`、`Tavily`、`Perplexity`、`serpstack`、`serper`、`Serply`、`DuckDuckGo`、`SearchApi`、`SerpApi`、`Bing`、`Jina`、`Exa`、`Sougou`、`Azure AI Search`、`Ollama Cloud` 等 15+ 搜索提供商，并可将结果直接注入聊天上下文。

- 🌐 **网页浏览能力**：使用 `#` 加网址的方式即可把网页内容纳入当前对话，进一步提升上下文丰富度和回答深度。

- 🎨 **图像生成与编辑集成**：支持 OpenAI DALL-E、Gemini、ComfyUI（本地）、AUTOMATIC1111（本地）等多种引擎，可完成图像生成及基于提示词的编辑工作流。

- ⚙️ **多模型并行对话**：可同时调用多个模型，利用各自优势协同回答，让输出更全面、更高质量。

- 🔐 **基于角色的访问控制（RBAC）**：通过受限权限保护访问，只有授权用户可以使用 Ollama，模型创建 / 拉取等操作也可仅限管理员使用。

- 🗄️ **灵活的数据库与存储方案**：支持 SQLite（可选加密）、PostgreSQL，以及 S3、Google Cloud Storage、Azure Blob Storage 等云存储后端，适合从本地到大规模部署的不同场景。

- 🔍 **高级向量数据库支持**：可从 ChromaDB、PGVector、Qdrant、Milvus、Elasticsearch、OpenSearch、Pinecone、S3Vector、Oracle 23ai 等 9 种方案中选择，以获得最佳 RAG 表现。

- 🔐 **企业级身份认证**：完整支持 LDAP / Active Directory、SCIM 2.0 自动预配、基于受信请求头的 SSO，以及 OAuth 提供商接入。可与 Okta、Azure AD、Google Workspace 等身份系统无缝集成。

- ☁️ **云原生集成**：原生支持 Google Drive 与 OneDrive / SharePoint 文件选择器，方便从企业云存储中导入文档。

- 📊 **生产级可观测性**：内置 OpenTelemetry，对 trace、metrics 与 logs 提供支持，可直接接入现有监控体系。

- ⚖️ **水平扩展能力**：基于 Redis 的会话管理与 WebSocket 支持，适合在负载均衡后进行多 worker、多节点部署。

- 🌐🌍 **多语言支持**：借助国际化（i18n）支持，以你熟悉的语言使用 Open WebUI。我们也欢迎更多贡献者一起扩展语言支持。

- 🧩 **Pipelines 与 Open WebUI 插件支持**：借助 [Pipelines Plugin Framework](https://github.com/open-webui/pipelines) 将自定义逻辑和 Python 库无缝接入 Open WebUI。只需启动 Pipelines 实例，把 OpenAI URL 指向 Pipelines，即可扩展无限可能。[示例](https://github.com/open-webui/pipelines/tree/main/examples) 包括**函数调用**、用户**限流**、使用 Langfuse 的**用量监控**、借助 LibreTranslate 的**实时翻译**、**有害消息过滤**等。

- 🌟 **持续更新**：项目会持续引入新功能、修复问题并不断优化体验。

想进一步了解 Open WebUI 的全部能力？欢迎查看 [Open WebUI 功能文档](https://docs.openwebui.com/features)。

---

我们非常感谢赞助者们的支持。正是这些帮助让我们得以持续维护并改进项目，为社区稳定交付高质量成果。谢谢你们！

## 如何安装 🚀

### 使用 Python pip 安装 🐍

你可以使用 Python 包管理器 `pip` 安装 Open WebUI。开始前请确认使用的是 **Python 3.11**，以避免兼容性问题。

1. **安装 Open WebUI**
   打开终端并执行：

   ```bash
   pip install open-webui
   ```

2. **运行 Open WebUI**
   安装完成后，执行：

   ```bash
   open-webui serve
   ```

服务启动后即可通过 [http://localhost:8080](http://localhost:8080) 访问 Open WebUI。

### 使用 Docker 快速开始 🐳

> [!NOTE]
> 请注意，在某些 Docker 环境下可能还需要额外配置。如果你遇到连接问题，可以参考 [Open WebUI 文档](https://docs.openwebui.com/) 中的详细指南。

> [!WARNING]
> 使用 Docker 安装 Open WebUI 时，请务必在命令中包含 `-v open-webui:/app/backend/data`。这一步非常关键，可确保数据库正确挂载，避免数据丢失。

> [!TIP]
> 如果你希望使用内置 Ollama 或 CUDA 加速，建议使用官方的 `:cuda` 或 `:ollama` 标签镜像。启用 CUDA 前，需要先在 Linux / WSL 系统上安装 [Nvidia CUDA container toolkit](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/)。

### 使用默认配置安装

- **如果 Ollama 就运行在本机**，使用以下命令：

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **如果 Ollama 运行在另一台服务器上**，使用以下命令：

  连接远程 Ollama 时，请把 `OLLAMA_BASE_URL` 改为对应服务器地址：

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **如需启用 Nvidia GPU 支持**，使用以下命令：

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
  ```

### 仅用于 OpenAI API 的安装方式

- **如果你只使用 OpenAI API**，请执行：

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

### 安装带内置 Ollama 支持的 Open WebUI

这种方式使用单个容器镜像同时打包 Open WebUI 与 Ollama，只需一条命令即可完成部署。请根据你的硬件环境选择：

- **启用 GPU**
  使用以下命令调用 GPU 资源：

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

- **仅 CPU**
  如果不使用 GPU，请改用：

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

两种命令都能让你以最省心的方式同时部署 Open WebUI 与 Ollama，快速完成开箱即用的环境搭建。

安装完成后，可通过 [http://localhost:3000](http://localhost:3000) 访问 Open WebUI。祝你使用愉快！😄

### 其他安装方式

我们还提供多种替代安装方案，包括非 Docker 的原生安装、Docker Compose、Kustomize 和 Helm。请访问 [Open WebUI 文档](https://docs.openwebui.com/getting-started/) 或加入我们的 [Discord 社区](https://discord.gg/5rJgQTnV4s) 获取完整指南。

如果你想搭建本地开发环境，也可以参考 [本地开发指南](https://docs.openwebui.com/getting-started/development)。

### 故障排查

遇到连接问题？可以先查阅 [Open WebUI 故障排查文档](https://docs.openwebui.com/troubleshooting/)。如需更多帮助，也欢迎加入 [Open WebUI Discord 社区](https://discord.gg/5rJgQTnV4s)。

#### Open WebUI：服务器连接错误

如果你遇到连接问题，通常是因为 WebUI Docker 容器无法在容器内部访问位于 `127.0.0.1:11434`（即 `host.docker.internal:11434`）的 Ollama 服务。你可以在 Docker 命令中加入 `--network=host` 来解决。注意此时访问端口会从 `3000` 变为 `8080`，对应地址为 `http://localhost:8080`。

**示例 Docker 命令：**

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### 让 Docker 安装保持最新

请查看 [Open WebUI 文档中的更新指南](https://docs.openwebui.com/getting-started/updating)。

### 使用 Dev 分支 🌙

> [!WARNING]
> `:dev` 分支包含最新但尚不稳定的功能与变更，可能存在 Bug 或未完成特性，请自行承担使用风险。

如果你想提前体验最新前沿功能，并能接受偶发不稳定情况，可以使用 `:dev` 标签：

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui --add-host=host.docker.internal:host-gateway --restart always ghcr.io/open-webui/open-webui:dev
```

### 离线模式

如果你在离线环境中运行 Open WebUI，可以将 `HF_HUB_OFFLINE` 环境变量设置为 `1`，以阻止程序尝试从互联网下载模型。

```bash
export HF_HUB_OFFLINE=1
```

## 接下来做什么？ 🌟

你可以在 [Open WebUI 路线图文档](https://docs.openwebui.com/roadmap/) 中了解即将到来的功能。

## 许可证 📜

本项目包含多种许可证下的代码。当前代码库既包含遵循 Open WebUI License 且要求保留 “Open WebUI” 品牌标识的组件，也包含历史贡献者按其原始许可证发布的内容。关于许可证变更记录以及各部分代码对应的适用条款，请参阅 [LICENSE_HISTORY](./LICENSE_HISTORY)。完整且最新的许可证信息请以 [LICENSE](./LICENSE) 和 [LICENSE_HISTORY](./LICENSE_HISTORY) 为准。

## 支持 💬

如果你有任何问题、建议，或需要帮助，请提交 issue，或加入 [Open WebUI Discord 社区](https://discord.gg/5rJgQTnV4s) 与我们交流。🤝

## Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

由 [Timothy Jaeryang Baek](https://github.com/tjbck) 创建。让我们一起把 Open WebUI 做得更棒！💪
