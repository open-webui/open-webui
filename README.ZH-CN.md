# Open WebUI 👋
[English](README.md) | 简体中文

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Follama-webui%2Follama-wbui&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tjbck)

**Open WebUI 是一个[可扩展](https://docs.openwebui.com/features/plugin/)、功能丰富且用户友好的自托管 AI 平台，旨在完全离线运行。**  
它支持多种 LLM 运行器，如 **Ollama** 和 **兼容 OpenAI 的 API**，并配备 **内置推理引擎** 用于 RAG，使其成为一个 **强大的 AI 部署解决方案**。

![Open WebUI 演示](./demo.gif)

> [!TIP]  
> **寻找[企业版](https://docs.openwebui.com/enterprise)？** – **[立即联系销售团队！](mailto:sales@openwebui.com)**
>
> 获取 **增强功能**，包括 **自定义主题和品牌**、**服务级别协议（SLA）支持**、**长期支持（LTS）版本**等！

了解更多信息，请访问我们的 [Open WebUI 文档](https://docs.openwebui.com/)。

## Open WebUI 主要功能 ⭐

- 🚀 **无忧安装**：可通过 Docker 或 Kubernetes（kubectl、kustomize 或 helm）轻松安装，支持 `:ollama` 和 `:cuda` 镜像标签。

- 🤝 **Ollama/OpenAI API 集成**：无缝集成 OpenAI 兼容 API，实现多样化的对话体验，支持 **LMStudio、GroqCloud、Mistral、OpenRouter 等**。

- 🛡️ **细粒度权限和用户组**：管理员可创建详细的用户角色和权限，提供安全的用户环境，同时支持个性化用户体验。

- 📱 **响应式设计**：在桌面 PC、笔记本电脑和移动设备上均能获得流畅体验。

- 📱 **渐进式 Web 应用（PWA）**：在移动设备上提供类似原生应用的体验，支持离线访问和流畅的用户界面。

- ✒️🔢 **Markdown 和 LaTeX 完全支持**：支持完整的 Markdown 和 LaTeX 语法，提升 LLM 交互体验。

- 🎤📹 **免提语音/视频通话**：集成语音和视频通话功能，实现更具互动性的聊天体验。

- 🛠️ **模型构建器**：通过 Web UI 轻松创建 Ollama 模型，支持自定义角色/代理、聊天元素和模型导入。

- 🐍 **原生 Python 函数调用**：支持工具工作区内置代码编辑器，允许添加纯 Python 函数，与 LLM 无缝集成。

- 📚 **本地 RAG 集成**：支持检索增强生成（RAG），可直接在聊天中加载文档或使用 `#` 命令访问文档库中的文件。

- 🔍 **RAG 网络搜索**：使用 `SearXNG`、`Google PSE`、`Brave Search`、`DuckDuckGo`、`TavilySearch`、`Bing` 等搜索引擎，直接在聊天中注入搜索结果。

- 🌐 **网页浏览能力**：使用 `#` 命令和 URL 直接在聊天中集成网页内容，增强互动体验。

- 🎨 **图像生成集成**：支持 AUTOMATIC1111 API、ComfyUI（本地）和 OpenAI 的 DALL-E（外部），让聊天更具视觉表现力。

- ⚙️ **多模型对话**：同时与多个模型交互，充分利用不同模型的优势，优化响应质量。

- 🔐 **基于角色的访问控制（RBAC）**：确保访问权限安全，限制非授权用户访问 Ollama，并对模型创建/拉取权限进行严格控制。

- 🌐🌍 **多语言支持**：支持国际化（i18n），欢迎社区贡献新语言！

- 🧩 **Pipelines 和插件支持**：通过 [Pipelines 插件框架](https://github.com/open-webui/pipelines) 轻松集成自定义逻辑和 Python 库，支持 **函数调用**、**用户速率限制**、**使用监控**、**实时翻译**、**有害消息过滤**等。

- 🌟 **持续更新**：我们致力于不断改进 Open WebUI，提供定期更新、修复和新功能。

想了解更多 Open WebUI 的功能？请查看[Open WebUI 文档](https://docs.openwebui.com/features)获取完整概述！

## 🔗 另请查看 Open WebUI Community！

欢迎探索我们的姊妹项目 [Open WebUI Community](https://openwebui.com/)，这里可以发现、下载和分享自定义的 Modelfiles，为 Open WebUI 聊天体验带来更多可能性！🚀

## 如何安装 🚀

### 通过 Python pip 安装 🐍

Open WebUI 可通过 pip（Python 包管理器）安装。在安装前，请确保使用 **Python 3.11** 以避免兼容性问题。

1. **安装 Open WebUI**：  
   打开终端，运行以下命令安装 Open WebUI：

   ```bash
   pip install open-webui
   ```

2. **运行 Open WebUI**：  
   安装完成后，执行以下命令启动 Open WebUI：

   ```bash
   open-webui serve
   ```

这将启动 Open WebUI 服务器，您可以在 [http://localhost:8080](http://localhost:8080) 访问它。

### 使用 Docker 快速启动 🐳

> [!NOTE]  
> 请注意，对于某些 Docker 环境，可能需要额外的配置。如果遇到连接问题，请参考 [Open WebUI 文档](https://docs.openwebui.com/) 中的详细指南。

> [!WARNING]  
> 在使用 Docker 安装 Open WebUI 时，请确保在 Docker 命令中包含 `-v open-webui:/app/backend/data`。此步骤至关重要，可确保数据库正确挂载，防止数据丢失。

> [!TIP]  
> 如果希望使用包含 Ollama 或支持 CUDA 加速的 Open WebUI，我们建议使用官方提供的 `:cuda` 或 `:ollama` 标签的镜像。要启用 CUDA，必须在 Linux/WSL 系统上安装 [Nvidia CUDA 容器工具包](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/)。

### 使用默认配置安装

- **如果 Ollama 安装在本机**，请使用以下命令：

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **如果 Ollama 安装在其他服务器**，请使用以下命令：

  要连接到另一台服务器上的 Ollama，请将“OLLAMA_BASE_URL”更改为服务器的 URL：

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **如需运行支持 Nvidia GPU 的 Open WebUI**，请使用以下命令：

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
  ```

### 仅用于 OpenAI API 的安装

- **如果仅使用 OpenAI API**，请使用以下命令：

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

### 安装包含 Ollama 支持的 Open WebUI

此安装方法使用单个容器镜像，将 Open WebUI 和 Ollama 捆绑在一起，实现简化安装。请根据硬件环境选择合适的命令：

- **支持 GPU**：  
  运行以下命令以利用 GPU 资源：

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

- **仅使用 CPU**：  
  如果未使用 GPU，请使用以下命令：

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

以上两种方式都可以实现 Open WebUI 和 Ollama 的内置无缝安装，确保您能快速启动和运行。

安装完成后，您可以在 [http://localhost:3000](http://localhost:3000) 访问 Open WebUI，尽情享受吧！😄

### 其他安装方法

我们提供多种安装方式，包括非 Docker 的本地安装、Docker Compose、Kustomize 和 Helm。请访问 [Open WebUI 文档](https://docs.openwebui.com/getting-started/) 或加入我们的 [Discord 社区](https://discord.gg/5rJgQTnV4s) 以获取详细指南。

### 故障排除

遇到连接问题？请参考我们的 [Open WebUI 文档](https://docs.openwebui.com/troubleshooting/)。如需进一步帮助或想加入我们的活跃社区，请访问 [Open WebUI Discord](https://discord.gg/5rJgQTnV4s)。

#### Open WebUI：服务器连接错误

如果您遇到连接问题，通常是因为 WebUI Docker 容器无法在容器内部访问 Ollama 服务器 (`127.0.0.1:11434` 或 `host.docker.internal:11434`)。您可以在 Docker 命令中使用 `--network=host` 选项来解决此问题。请注意，这会将端口从 3000 更改为 8080，因此访问链接应为 `http://localhost:8080`。

**示例 Docker 命令**：

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### 保持 Docker 安装为最新版本

如果您希望将本地 Docker 安装更新至最新版本，可以使用 [Watchtower](https://containrrr.dev/watchtower/) 进行更新：

```bash
docker run --rm --volume /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --run-once open-webui
```

在命令的最后部分，如果您的容器名称不同，请将 `open-webui` 替换为您的容器名称。

请参考 [Open WebUI 文档](https://docs.openwebui.com/getting-started/updating) 中的更新指南。

### 使用 Dev 分支 🌙

> [!WARNING]  
> `:dev` 分支包含最新的非稳定功能和改动。请谨慎使用，因为它可能存在 Bug 或未完成的功能。

如果您想尝试最新的功能，并且可以接受偶尔的不稳定性，可以使用 `:dev` 标签运行以下命令：

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui --add-host=host.docker.internal:host-gateway --restart always ghcr.io/open-webui/open-webui:dev
```

### 离线模式

如果您在离线环境下运行 Open WebUI，可以设置 `HF_HUB_OFFLINE` 环境变量为 `1`，以防止尝试从互联网下载模型。

```bash
export HF_HUB_OFFLINE=1
```

## 接下来？🌟

在 [Open WebUI 文档](https://docs.openwebui.com/roadmap/) 中查看即将推出的功能路线图。

## 许可证 📜

本项目遵循 [BSD-3-Clause 许可证](LICENSE) - 详情请参阅 [LICENSE](LICENSE) 文件。📄

## 支持 💬

如果您有任何问题、建议或需要帮助，请提交 Issue，或加入我们的  
[Open WebUI Discord 社区](https://discord.gg/5rJgQTnV4s) 与我们交流！🤝

## Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

由 [Timothy Jaeryang Baek](https://github.com/tjbck) 创建 - 让我们一起让 Open WebUI 变得更加精彩！💪
