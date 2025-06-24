# 🚀 Quick Setup Guide (Custom Docker Configuration)

This repo includes a **custom Docker setup** with **Open WebUI + SearXNG + Ollama + Pipelines** containers plus easy management scripts.

## Prerequisites
- Docker and Docker Compose installed
- OpenAI API key (optional, for additional models)

## 🎯 What You Get Out of the Box
- **Open WebUI**: Web interface for chatting with AI models
- **Ollama**: Local AI models (llama2, mistral, etc.)
- **SearXNG**: Private web search engine
- **Pipelines**: Function calling (calculator, weather, time) + extensibility framework

## Quick Start
1. **Set up environment** (optional):
   ```bash
   echo "OPENAI_API_KEY=your_actual_api_key_here" > .env
   ```

2. **Start everything**:
   ```bash
   ./start.sh
   ```

3. **Download AI models**:
   ```bash
   ./manage.sh pull llama2 # or llama3.2, mistral, etc.
   ```

4. **Access the app**: http://localhost:3000

## Management Scripts
- `./start.sh` - Start all containers
- `./stop.sh` - Stop containers (options: `--hard`, `--clean`)
- `./manage.sh restart` - Restart everything
- `./manage.sh logs` - View live logs
- `./manage.sh status` - Check container status
- `./manage.sh models` - List downloaded models
- `./manage.sh pull <model>` - Download new models
- `./manage.sh pipelines` - List installed pipelines
- `./manage.sh test-pipeline` - Test pipeline connection
- `./manage.sh pipeline-logs` - View pipeline container logs

## What's Running
- **Open WebUI**: http://localhost:3000 (main interface)
- **SearXNG**: http://localhost:8080 (web search)
- **Ollama**: http://localhost:11434 (AI models API)
- **Pipelines**: http://localhost:9099 (function calling & extensions)

## 🛠️ Complete First Time Setup

### 1. Start Containers
```bash
./start.sh
```
Wait for all containers to start (about 30 seconds).

### 2. Create Admin Account
1. Go to http://localhost:3000
2. Create your admin account

### 3. Connect Pipelines (IMPORTANT!)
1. Go to **Settings → Connections → OpenAI API**
2. Click **"+ Add Connection"**
3. Configure:
   - **API Base URL**: `http://host.docker.internal:9099`
   - **API Key**: `0p3n-w3bu!`
4. **Save** - you should see a green checkmark and "Pipelines" label

### 4. Configure Web Search (Optional)
1. Go to **Admin Settings → Web Search**
2. Set engine to **"SearXNG"**
3. Set URL to: `http://host.docker.internal:8080/search?q=<query>`

### 5. Download Models
```bash
./manage.sh pull llama2        # Basic model
./manage.sh pull llama3.2      # Better model
./manage.sh pull mistral       # Fast model
```

### 6. Test Everything!
Try these in Open WebUI chat:
- `"What time is it?"` ⏰ (function calling)
- `"Calculate 123 * 456"` 🧮 (function calling)
- `"What's the weather in New York?"` 🌤️ (needs OpenWeatherMap API key)

## 🔧 Pipeline Features (The Cool Stuff!)

**Pipelines** add superpowers to your AI chats:

### 🎯 Function Calling (Pre-installed)
- **Calculator**: Real math instead of AI guessing
- **Time**: Actual current time
- **Weather**: Live weather data (configure API key in Admin Panel → Pipelines)

### 🚀 What Pipelines Enable
- **RAG Systems**: Upload documents, get AI to reference them
- **Web Search Integration**: AI can search the internet for current info
- **Custom APIs**: Connect to databases, services, internal tools
- **Safety Filters**: Block inappropriate content, rate limiting
- **Monitoring**: Track usage, log conversations
- **Custom Functions**: Add any Python functionality

### 🧪 Testing Pipeline Functions

**Built-in Functions** (work immediately):
```
"What time is it?"
"Calculate 15 * 23 + 45"
"What's 2 to the power of 10?"
"What's the tip for a $85 bill at 18%?"
```

**Weather** (configure OpenWeatherMap API key first):
```
"What's the weather in New York?"
"How's the weather in London?"
"What's the temperature in Tokyo?"
```

### ⚙️ Configure Weather Function
1. Get free API key: https://openweathermap.org/api
2. Go to **Admin Panel → Pipelines → My Tools Pipeline**
3. Add your API key to "Weather API Key" field
4. Save

## 📁 Files Structure
- `docker-compose.custom.yml` - Container configuration
- `searxng_settings.yml` - SearXNG search engine settings
- `.env` - Environment variables (create this file)
- `start.sh` - Startup script
- `stop.sh` - Shutdown script  
- `manage.sh` - Management commands

## 🔧 Troubleshooting

### Pipelines Not Detected
**Problem**: Admin Panel → Pipelines shows "Pipelines not detected"
**Solution**: 
1. Check connection in Settings → Connections
2. API URL must be: `http://host.docker.internal:9099`
3. API Key must be: `0p3n-w3bu!`
4. Look for green checkmark and "Pipelines" label

### Function Calling Not Working
**Problem**: AI ignores calculator/time requests
**Solution**:
1. Verify pipelines connection (above)
2. Check pipeline logs: `./manage.sh pipeline-logs`
3. In Admin Panel → Pipelines, configure "Task Model" (try `gpt-3.5-turbo`)

### Container Connection Issues
**Problem**: Containers can't reach each other
**Solution**:
1. Use `host.docker.internal` instead of `localhost` in URLs
2. Check container status: `./manage.sh status`
3. Restart everything: `./manage.sh restart`

### Weather API Not Working
**Problem**: Weather queries fail
**Solution**:
1. Get free OpenWeatherMap API key
2. Configure in Admin Panel → Pipelines → My Tools Pipeline
3. Wait 10-15 minutes for API key activation

## 🚀 Advanced Usage

### Add More Pipelines
```bash
# Wikipedia integration
./manage.sh install-pipeline https://github.com/open-webui/pipelines/blob/main/examples/pipelines/integrations/wikipedia_pipeline.py

# Web search pipeline
./manage.sh install-pipeline https://github.com/open-webui/pipelines/blob/main/examples/filters/web_search_filter_pipeline.py
```

### Monitor Activity
```bash
# View all logs
./manage.sh logs

# View just pipeline activity
./manage.sh pipeline-logs

# Check what's running
./manage.sh status
```

### Clean Restart
```bash
# Stop everything and remove containers
./stop.sh --hard

# Start fresh
./start.sh
```

## ❓ Common Questions

**Q: What's the difference between this and regular Open WebUI?**
A: This adds pipelines for function calling (calculator, weather, time) plus SearXNG for private web search.

**Q: Do I need OpenAI API key?**
A: No! Works with local Ollama models. OpenAI key is optional for additional models.

**Q: Can I add custom functions?**
A: Yes! Pipelines framework lets you add any Python functionality.

**Q: Is this secure?**
A: Yes, everything runs locally. SearXNG doesn't track you, Ollama is local, pipelines are sandboxed.

**Q: What if I break something?**
A: Run `./stop.sh --clean` to reset everything, then `./start.sh` to start fresh.

---

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

**Open WebUI is an [extensible](https://docs.openwebui.com/features/plugin/), feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

![Open WebUI Demo](./demo.gif)

> [!TIP]  
> **Looking for an [Enterprise Plan](https://docs.openwebui.com/enterprise)?** – **[Speak with Our Sales Team Today!](mailto:sales@openwebui.com)**
>
> Get **enhanced capabilities**, including **custom theming and branding**, **Service Level Agreement (SLA) support**, **Long-Term Support (LTS) versions**, and **more!**

For more information, be sure to check out our [Open WebUI Documentation](https://docs.openwebui.com/).

## Key Features of Open WebUI ⭐

- 🚀 **Effortless Setup**: Install seamlessly using Docker or Kubernetes (kubectl, kustomize or helm) for a hassle-free experience with support for both `:ollama` and `:cuda` tagged images.

- 🤝 **Ollama/OpenAI API Integration**: Effortlessly integrate OpenAI-compatible APIs for versatile conversations alongside Ollama models. Customize the OpenAI API URL to link with **LMStudio, GroqCloud, Mistral, OpenRouter, and more**.

- 🛡️ **Granular Permissions and User Groups**: By allowing administrators to create detailed user roles and permissions, we ensure a secure user environment. This granularity not only enhances security but also allows for customized user experiences, fostering a sense of ownership and responsibility amongst users.

- 📱 **Responsive Design**: Enjoy a seamless experience across Desktop PC, Laptop, and Mobile devices.

- 📱 **Progressive Web App (PWA) for Mobile**: Enjoy a native app-like experience on your mobile device with our PWA, providing offline access on localhost and a seamless user interface.

- ✒️🔢 **Full Markdown and LaTeX Support**: Elevate your LLM experience with comprehensive Markdown and LaTeX capabilities for enriched interaction.

- 🎤📹 **Hands-Free Voice/Video Call**: Experience seamless communication with integrated hands-free voice and video call features, allowing for a more dynamic and interactive chat environment.

- 🛠️ **Model Builder**: Easily create Ollama models via the Web UI. Create and add custom characters/agents, customize chat elements, and import models effortlessly through [Open WebUI Community](https://openwebui.com/) integration.

- 🐍 **Native Python Function Calling Tool**: Enhance your LLMs with built-in code editor support in the tools workspace. Bring Your Own Function (BYOF) by simply adding your pure Python functions, enabling seamless integration with LLMs.

- 📚 **Local RAG Integration**: Dive into the future of chat interactions with groundbreaking Retrieval Augmented Generation (RAG) support. This feature seamlessly integrates document interactions into your chat experience. You can load documents directly into the chat or add files to your document library, effortlessly accessing them using the `#` command before a query.

- 🔍 **Web Search for RAG**: Perform web searches using providers like `SearXNG`, `Google PSE`, `Brave Search`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `TavilySearch`, `SearchApi` and `Bing` and inject the results directly into your chat experience.

- 🌐 **Web Browsing Capability**: Seamlessly integrate websites into your chat experience using the `#` command followed by a URL. This feature allows you to incorporate web content directly into your conversations, enhancing the richness and depth of your interactions.

- 🎨 **Image Generation Integration**: Seamlessly incorporate image generation capabilities using options such as AUTOMATIC1111 API or ComfyUI (local), and OpenAI's DALL-E (external), enriching your chat experience with dynamic visual content.

- ⚙️ **Many Models Conversations**: Effortlessly engage with various models simultaneously, harnessing their unique strengths for optimal responses. Enhance your experience by leveraging a diverse set of models in parallel.

- 🔐 **Role-Based Access Control (RBAC)**: Ensure secure access with restricted permissions; only authorized individuals can access your Ollama, and exclusive model creation/pulling rights are reserved for administrators.

- 🌐🌍 **Multilingual Support**: Experience Open WebUI in your preferred language with our internationalization (i18n) support. Join us in expanding our supported languages! We're actively seeking contributors!

- 🧩 **Pipelines, Open WebUI Plugin Support**: Seamlessly integrate custom logic and Python libraries into Open WebUI using [Pipelines Plugin Framework](https://github.com/open-webui/pipelines). Launch your Pipelines instance, set the OpenAI URL to the Pipelines URL, and explore endless possibilities. [Examples](https://github.com/open-webui/pipelines/tree/main/examples) include **Function Calling**, User **Rate Limiting** to control access, **Usage Monitoring** with tools like Langfuse, **Live Translation with LibreTranslate** for multilingual support, **Toxic Message Filtering** and much more.

- 🌟 **Continuous Updates**: We are committed to improving Open WebUI with regular updates, fixes, and new features.

Want to learn more about Open WebUI's features? Check out our [Open WebUI documentation](https://docs.openwebui.com/features) for a comprehensive overview!

## Sponsors 🙌

#### Emerald

<table>
  <tr>
    <td>
      <a href="https://n8n.io/" target="_blank">
        <img src="https://docs.openwebui.com/sponsors/logos/n8n.png" alt="n8n" style="width: 8rem; height: 8rem; border-radius: .75rem;" />
      </a>
    </td>
    <td>
      <a href="https://n8n.io/">n8n</a> • Does your interface have a backend yet?<br>Try <a href="https://n8n.io/">n8n</a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://warp.dev/open-webui" target="_blank">
        <img src="https://docs.openwebui.com/sponsors/logos/warp.png" alt="Warp" style="width: 8rem; height: 8rem; border-radius: .75rem;" />
      </a>
    </td>
    <td>
      <a href="https://warp.dev/open-webui">Warp</a> • The intelligent terminal for developers
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://tailscale.com/blog/self-host-a-local-ai-stack/?utm_source=OpenWebUI&utm_medium=paid-ad-placement&utm_campaign=OpenWebUI-Docs" target="_blank">
        <img src="https://docs.openwebui.com/sponsors/logos/tailscale.png" alt="Tailscale" style="width: 8rem; height: 8rem; border-radius: .75rem;" />
      </a>
    </td>
    <td>
      <a href="https://tailscale.com/blog/self-host-a-local-ai-stack/?utm_source=OpenWebUI&utm_medium=paid-ad-placement&utm_campaign=OpenWebUI-Docs">Tailscale</a> • Connect self-hosted AI to any device with Tailscale
    </td>
  </tr>
</table>

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

Look at the [Local Development Guide](https://docs.openwebui.com/getting-started/advanced-topics/development) for instructions on setting up a local development environment.

### Troubleshooting

Encountering connection issues? Our [Open WebUI Documentation](https://docs.openwebui.com/troubleshooting/) has got you covered. For further assistance and to join our vibrant community, visit the [Open WebUI Discord](https://discord.gg/5rJgQTnV4s).

#### Open WebUI: Server Connection Error

If you're experiencing connection issues, it's often due to the WebUI docker container not being able to reach the Ollama server at 127.0.0.1:11434 (host.docker.internal:11434) inside the container. Use the `--network=host` flag in your docker command to resolve this. Note that the port changes from 3000 to 8080, resulting in the link: `http://localhost:8080`.

**Example Docker Command**:

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### Keeping Your Docker Installation Up-to-Date

In case you want to update your local Docker installation to the latest version, you can do it with [Watchtower](https://containrrr.dev/watchtower/):

```bash
docker run --rm --volume /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --run-once open-webui
```

In the last part of the command, replace `open-webui` with your container name if it is different.

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

This project is licensed under the [Open WebUI License](LICENSE), a revised BSD-3-Clause license. You receive all the same rights as the classic BSD-3 license: you can use, modify, and distribute the software, including in proprietary and commercial products, with minimal restrictions. The only additional requirement is to preserve the "Open WebUI" branding, as detailed in the LICENSE file. For full terms, see the [LICENSE](LICENSE) document. 📄

## Support 💬

If you have any questions, suggestions, or need assistance, please open an issue or join our
[Open WebUI Discord community](https://discord.gg/5rJgQTnV4s) to connect with us! 🤝

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
