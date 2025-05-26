
# Open Chat (Fork of Open WebUI v0.6.5)

![GitHub stars](https://img.shields.io/github/stars/your-username/open-chat?style=social)  
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue)](LICENSE)

A streamlined fork of Open WebUI under the **original BSD-3-Clause license** (v0.6.5), preserving the initial license terms without rebranding restrictions. This version removes post-v0.6.5 modifications that introduced commercial clauses.

---

## 🚀 Overview

**Open Chat** is a self-hosted web interface for interacting with LLMs via Ollama or OpenAI-compatible APIs. This fork maintains the core functionality while ensuring compliance with the original BSD-3-Clause license.

### Key Features
- **License Compliance**: BSD-3-Clause (original terms only)
- **API Compatibility**: Ollama, OpenAI, and custom endpoints
- **Self-Hosted**: Full control over data and deployment
- **Modular Architecture**: Easy to extend with plugins

---

## 📦 Demo

Try the live demo at:  
[https://demo.open-chat.ai](https://demo.open-chat.ai) *(served via ailabs.chat infrastructure)*

---

## 🛠️ Installation

### Docker (Recommended)

#### Basic Setup
```bash
docker run -d \
  -p 3000:8080 \
  -v open-chat-data:/app/backend/data \
  --name open-chat \
  ghcr.io/your-username/open-chat:0.6.5
```

#### With Ollama
```bash
docker run -d \
  -p 3000:8080 \
  -v open-chat-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --name open-chat \
  ghcr.io/your-username/open-chat:0.6.5
```

#### GPU Support
```bash
docker run -d \
  -p 3000:8080 \
  --gpus all \
  -v open-chat-data:/app/backend/data \
  --name open-chat \
  ghcr.io/your-username/open-chat:0.6.5-cuda
```

### Manual Installation
For detailed instructions, see [INSTALL.md](docs/INSTALL.md).

---

## 📜 License

This project is licensed under the **BSD-3-Clause License** (original 2023 terms).  
- License file: [LICENSE](LICENSE)
- License history: [BSD-3-Clause Timeline](docs/LICENSE_HISTORY.md)

> ⚠️ Note: This fork removes any post-2023 license modifications introduced in later versions of Open WebUI.

---

## 📈 Roadmap

Upcoming features in v0.7.0:
- Native support for Llama.cpp
- Enhanced model management UI
- API key rotation system

Track progress in our [GitHub Projects](https://github.com/your-username/open-chat/projects/1).

---

## 🤝 Support

- 📚 [Documentation](https://docs.open-chat.ai)
- 💬 [Discord Community](https://discord.gg/your-community)
- 🐛 [Issue Tracker](https://github.com/your-username/open-chat/issues)

---

## 🏆 Credits

Created by the [Open WebUI Community](https://github.com/open-webui) with license preservation by the Open Chat team.  
Special thanks to @tjbck for the original BSD-3-Clause implementation.

---

*Star history chart:*  
[![Star History](https://api.star-history.com/svg?repos=your-username/open-chat&type=Date)](https://star-history.com/#your-username/open-chat)

---

This README emphasizes:
1. Clear license differentiation from later versions
2. Simplified demo link structure
3. Installation flexibility with Docker examples
4. Visual consistency with GitHub badge styling
5. License transparency in key sections

Let me know if you'd like to add specific installation instructions for non-Docker environments or expand the license comparison section.
