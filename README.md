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

**Open WebUI is an [extensible](https://docs.openwebui.com/features/extensibility/plugin), feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

Passionate about open-source AI? [Join our team →](https://careers.openwebui.com/)

![Open WebUI Demo](./demo.png)

> [!TIP]  
> **Looking for an [Enterprise Plan](https://docs.openwebui.com/enterprise)?** – **[Speak with Our Sales Team Today!](https://docs.openwebui.com/enterprise)**
>
> Get **enhanced capabilities**, including **custom theming and branding**, **Service Level Agreement (SLA) support**, **Long-Term Support (LTS) versions**, and **more!**

For more information, be sure to check out our [Open WebUI Documentation](https://docs.openwebui.com/).

## Key Features of Open WebUI ⭐

- 🚀 **Effortless Setup**: Install seamlessly via pip, uv, Docker, or Kubernetes (kubectl, kustomize, or helm) for a hassle-free experience — with `:ollama` and `:cuda` tagged images available for container deployments.

- 🤝 **Broad Model & API Integration**: Connect any OpenAI Completions or Open Responses-compatible API alongside local Ollama models. Point the API URL at **LMStudio, GroqCloud, Mistral, OpenRouter, vLLM, and many more** to mix and match providers freely.

- 🔐 **Granular RBAC & User Groups**: Administrators define detailed roles, groups, and permissions, giving each user exactly the access they should have — secure by default, with tailored experiences per group and admin-only rights for sensitive actions like model creation and pulling.

- 🧩 **Plugin Support — Build Almost Anything**: Extend Open WebUI with native plugins, each specialized for its job: **Filters** to intercept and transform requests and responses, **Actions** to add custom buttons and interactive flows, **Pipes** to build entirely custom models and pipelines with custom logic, and **Tools** to give models real capabilities. Connect external services through **MCP** (native Streamable HTTP for Model Context Protocol servers), **MCPO**, and **OpenAPI tool servers** (auto-discover tools from any OpenAPI-compatible endpoint). Add **Skills** (Markdown instruction sets that teach models how to approach tasks) and **Prompts** (slash-command templates with typed input variables and versioning). With these building blocks you can create custom integrations, rate limits, human-in-the-loop approval popups, data connections, per-user usage budgets, custom interfaces, and much more. If you can imagine it, you can most likely build it.

- 🤖 **Models & Agents**: Wrap any base model with custom instructions, bound tools, and knowledge to build specialized agents — a "Code Reviewer" with your linting rules baked in, a "Meeting Summarizer" with your company's template, a "Python Tutor" that always uses your style guide. Each agent is a configuration preset (system prompt, tools, knowledge, and parameters in one package), with dynamic variables like `{{ USER_NAME }}` and `{{ CURRENT_DATE }}` injected automatically, per-user/group access control, and global defaults across all models. Build characters and import community presets through [Open WebUI Community](https://openwebui.com/) integration.

- 📝 **Notes**: A dedicated workspace for content that lives outside any single conversation — draft with a rich Markdown/Rich-Text editor and floating formatting toolbar, use AI to rewrite or improve selected text in place, and attach notes to any chat for full-fidelity context injection (no chunking, no vector search). Models can search, read, and update notes autonomously.

- 📢 **Channels**: Real-time shared spaces where your team and AI models think together in one timeline. Tag `@gpt-4o` to draft a plan, then tag `@claude` to critique it — everyone sees both responses. Includes threads, reactions, and pins, public/private/group/DM channels with access control, and AI that can search and synthesize across channels autonomously.

- 🧠 **Persistent Memory**: The AI remembers facts about you across conversations, carrying context from one chat to the next.

- ⏱️ **Automations & Scheduled Prompts**: Schedule prompts to run automatically on recurring schedules, and let models maintain structured task lists to work through multi-step workflows.

- 📱 **Responsive Design & PWA**: Enjoy a seamless experience across desktop, laptop, and mobile, with a Progressive Web App that delivers a native app-like feel and offline access on localhost.

- ✒️🔢 **Full Markdown and LaTeX Support**: Elevate your LLM experience with comprehensive Markdown and LaTeX capabilities for enriched interaction.

- 🎤📹 **Hands-Free Voice/Video Call**: Communicate seamlessly with integrated voice and video calls, using multiple Speech-to-Text providers (Local Whisper, OpenAI, Deepgram, Azure) and Text-to-Speech engines (Azure, ElevenLabs, OpenAI, Transformers, WebAPI) for dynamic, interactive chats.

- 💾 **Persistent Artifact Storage**: Built-in key-value storage API for artifacts, enabling journals, trackers, leaderboards, and collaborative tools with both personal and shared data scopes across sessions.

- 📚 **Local RAG Integration**: Bring Retrieval Augmented Generation right into your chats, backed by your choice of 9 vector databases and multiple content-extraction engines (Tika, Docling, Document Intelligence, Mistral OCR, PaddleOCR-vl, external loaders). Use hybrid search (BM25 + vector) with cross-encoder reranking for precision, or full-context mode to inject entire documents with no chunking. Load documents directly into chat or add files to your library and pull them in with the `#` command before a query — and keep those libraries continuously synced from 45+ external sources with **oikb** (see the Ecosystem section below).

- 🔍 **Web Search for RAG**: Search the web through dozens of providers — `SearXNG`, `Brave Search`, `Kagi`, `Mojeek`, `Tavily`, `Perplexity`, `Firecrawl`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `SearchApi`, `SerpApi`, `Bing`, `Jina`, `Exa`, `Sougou`, `Azure AI Search`, `Ollama Cloud`, and more — injecting results directly into the conversation.

- 🌐 **Web Browsing Capability**: Pull websites into chat with the `#` command followed by a URL, or let the model fetch them on its own when it needs to — adding richness and depth to your interactions.

- 🎨 **Image Generation & Editing**: Create and edit images with multiple engines including OpenAI DALL·E, Gemini, ComfyUI (local), and AUTOMATIC1111 (local), supporting both generation and prompt-based editing workflows.

- ⚙️ **Multi-Model Conversations**: Engage several models at once, harnessing their individual strengths in parallel for the best possible responses.

- 📊 **Usage Analytics & Model Evaluation**: Built-in admin dashboards track message volume, token consumption, and cost across users and models. Evaluate models head-to-head with a built-in arena, A/B testing, and ELO-based leaderboards to find what works best for your team.

- 🗄️ **Flexible Database & Storage**: Choose SQLite (with optional encryption) or PostgreSQL for your database, and store files locally or on S3, Google Cloud Storage, or Azure Blob Storage for scalable deployments.

- 🔍 **Advanced Vector Database Support**: Pick from 9 vector databases — ChromaDB, PGVector, Qdrant, Milvus, Elasticsearch, OpenSearch, Pinecone, S3Vector, and Oracle 23ai — to tune RAG performance to your stack.

- 🔐 **Enterprise Authentication & Provisioning**: Full LDAP/Active Directory integration, SSO via trusted headers and OAuth providers, and automated user lifecycle management through SCIM 2.0 — for seamless integration with identity providers like Okta, Azure AD, and Google Workspace.

- ☁️ **Cloud-Native File Integration**: Native Google Drive and OneDrive/SharePoint file picking for seamless document import from enterprise cloud storage.

- 📊 **Production Observability**: Built-in OpenTelemetry support for traces, metrics, and logs, plugging into your existing monitoring stack.

- ⚖️ **Horizontal Scalability**: Redis-backed session management and WebSocket support for multi-worker, multi-node deployments behind load balancers.

- 🌐🌍 **Multilingual Support**: Use Open WebUI in your preferred language through our internationalization (i18n) support — and help us add more; we're actively seeking contributors!

- 🌟 **Continuous Updates**: We're committed to improving Open WebUI with regular updates, fixes, and new features.

- 🛡️ **Transparent Security Process**: Security reports are triaged, fixed, and published as open advisories through a documented responsible-disclosure process — see our [Security Policy](https://github.com/open-webui/open-webui/security).

Want to learn more about Open WebUI's features? Check out our [Open WebUI documentation](https://docs.openwebui.com/features) for a comprehensive overview!

## The Open WebUI Ecosystem 🌐

Open WebUI is the core, surrounded by companion apps and infrastructure that extend what your AI can do, what it can reach, and where you run it:

- ⚡ **Open Terminal — Give Your AI a Real Computer** — [open-webui/open-terminal](https://github.com/open-webui/open-terminal): A self-hosted computing environment that plugs directly into Open WebUI, giving the AI a place to write code, run it, read the output, fix errors, and iterate — all inside the chat. Analyze spreadsheets and PDFs, build and live-preview websites, clone repos and run tests, automate file and system tasks. Run it sandboxed in Docker or bare-metal for full machine access, with a built-in file browser sidebar in Open WebUI.

- 🔐 **Terminals — Per-User Container Orchestration** **· Enterprise** — [open-webui/terminals](https://github.com/open-webui/terminals): Run Open Terminal safely for a whole team. Every user gets their own fully isolated container — separate credentials, resource limits, and network rules — with automatic lifecycle management (spin-up on connect, proxying, limit enforcement, cleanup). Define policy-based environments on Docker or Kubernetes. Per-user isolation makes this the production-grade, hardened way to run Open Terminal for a team.
> [!IMPORTANT]
> Production use requires an **Open WebUI Enterprise License with Terminals access**. [Contact the Open WebUI team](https://docs.openwebui.com/enterprise) to get started.

- 💻 **cptr — Talk to Your Computer From Anywhere** — [open-webui/computer](https://github.com/open-webui/computer): A standalone, mobile-first computer and coding agent that runs on the machine you own — files, terminal, and git in a browser tab, reachable from your phone. Connect it into Open WebUI as a model and chat with your own computer directly, or reach it from Telegram, WhatsApp, and more — control your machine and ship from anywhere.

- 🔄 **oikb — Connect Everything** — [open-webui/oikb](https://github.com/open-webui/oikb): Feed your Knowledge Bases from 45+ sources — GitHub, Confluence, ServiceNow, Salesforce, Jira, Slack, SharePoint, Notion, and many more — keeping the tools your team already uses continuously in sync with Open WebUI.

- 🖥️ **Native Desktop App** — [open-webui/desktop](https://github.com/open-webui/desktop): Run Open WebUI as a native app on macOS, Windows, and Linux — no Docker, no terminal, just download and launch. System-wide Spotlight chat bar with screenshot capture, push-to-talk voice from any app, and optional fully-local inference via a built-in llama.cpp engine.

Want to learn more about Open WebUI's Ecosystem? Check out our [Open WebUI documentation](https://docs.openwebui.com) for more details!

---

We are incredibly grateful for the generous support of our sponsors. Their contributions help us to maintain and improve our project, ensuring we can continue to deliver quality work to our community. Thank you!

## How to Install 🚀

### Installation via Python pip 🐍

Open WebUI can be installed using pip, the Python package installer. Before proceeding, ensure you're using **Python 3.11** to avoid compatibility issues.

1. **Install Open WebUI**:
   Open your terminal and run the following command to install Open WebUI:

   ```bash
   pip install open-webui
   ```

2. **Running Open WebUI**:
   After installation, you can start Open WebUI by executing:

   ```bash
   open-webui serve
   ```

This will start the Open WebUI server, which you can access at [http://localhost:8080](http://localhost:8080)

### Quick Start with Docker 🐳

> [!NOTE]  
> Please note that for certain Docker environments, additional configurations might be needed. If you encounter any connection issues, our detailed guide on [Open WebUI Documentation](https://docs.openwebui.com/) is ready to assist you.

> [!WARNING]
> When using Docker to install Open WebUI, make sure to include the `-v open-webui:/app/backend/data` in your Docker command. This step is crucial as it ensures your database is properly mounted and prevents any loss of data.

> [!TIP]  
> If you wish to utilize Open WebUI with Ollama included or CUDA acceleration, we recommend utilizing our official images tagged with either `:cuda` or `:ollama`. To enable CUDA, you must install the [Nvidia CUDA container toolkit](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/) on your Linux/WSL system.

### Installation with Default Configuration

- **If Ollama is on your computer**, use this command:

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **If Ollama is on a Different Server**, use this command:

  To connect to Ollama on another server, change the `OLLAMA_BASE_URL` to the server's URL:

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **To run Open WebUI with Nvidia GPU support**, use this command:

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
  ```

### Installation for OpenAI API Usage Only

- **If you're only using OpenAI API**, use this command:

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

### Installing Open WebUI with Bundled Ollama Support

This installation method uses a single container image that bundles Open WebUI with Ollama, allowing for a streamlined setup via a single command. Choose the appropriate command based on your hardware setup:

- **With GPU Support**:
  Utilize GPU resources by running the following command:

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

- **For CPU Only**:
  If you're not using a GPU, use this command instead:

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

Both commands facilitate a built-in, hassle-free installation of both Open WebUI and Ollama, ensuring that you can get everything up and running swiftly.

After installation, you can access Open WebUI at [http://localhost:3000](http://localhost:3000). Enjoy! 😄

### Other Installation Methods

We offer various installation alternatives, including non-Docker native installation methods, Docker Compose, Kustomize, and Helm. Visit our [Open WebUI Documentation](https://docs.openwebui.com/getting-started/) or join our [Discord community](https://discord.gg/5rJgQTnV4s) for comprehensive guidance.

### Troubleshooting

Encountering connection issues? Our [Open WebUI Documentation](https://docs.openwebui.com/troubleshooting/) has got you covered. For further assistance and to join our vibrant community, visit the [Open WebUI Discord](https://discord.gg/5rJgQTnV4s).

#### Open WebUI: Server Connection Error

If you're experiencing connection issues, it’s often due to the WebUI docker container not being able to reach the Ollama server at 127.0.0.1:11434 (host.docker.internal:11434) inside the container . Use the `--network=host` flag in your docker command to resolve this. Note that the port changes from 3000 to 8080, resulting in the link: `http://localhost:8080`.

**Example Docker Command**:

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### Keeping Your Docker Installation Up-to-Date

Check our Updating Guide available in our [Open WebUI Documentation](https://docs.openwebui.com/getting-started/updating).

### Using the Dev Branch 🌙

> [!WARNING]
> The `:dev` branch contains the latest unstable features and changes. Use it at your own risk as it may have bugs or incomplete features.

If you want to try out the latest bleeding-edge features and are okay with occasional instability, you can use the `:dev` tag like this:

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui --add-host=host.docker.internal:host-gateway --restart always ghcr.io/open-webui/open-webui:dev
```

### Offline Mode

If you are running Open WebUI in an offline environment, you can set the `HF_HUB_OFFLINE` environment variable to `1` to prevent attempts to download models from the internet.

```bash
export HF_HUB_OFFLINE=1
```

## What's Next? 🌟

Discover upcoming features on our roadmap in the [Open WebUI Documentation](https://docs.openwebui.com/roadmap/).

## License 📜

This project contains code under multiple licenses. The current codebase includes components licensed under the Open WebUI License with an additional requirement to preserve the "Open WebUI" branding, as well as prior contributions under their respective original licenses. For a detailed record of license changes and the applicable terms for each section of the code, please refer to [LICENSE_HISTORY](./LICENSE_HISTORY). For complete and updated licensing details, please see the [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) files.

## Support 💬

If you have any questions, suggestions, or need assistance, please open an issue or join our
[Open WebUI Discord community](https://discord.gg/5rJgQTnV4s) to connect with us! 🤝

## Security 🛡️

If you believe you've found a security vulnerability — or something that isn't strictly a vulnerability but shouldn't be disclosed publicly — [reach out confidentially through our responsible disclosure program on GitHub](https://github.com/open-webui/open-webui/security).
We accept reports only through GitHub, not through any other platform.
Thank you for helping us keep Open WebUI secure!

## Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

Created by [Timothy Jaeryang Baek](https://github.com/tjbck) - Let's make Open WebUI even more amazing together! 💪
