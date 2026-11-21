<h2>Open WebUI</h2>

<p>Open WebUI är <a href="https://docs.openwebui.com/"><strong>ett hem för AI</strong></a>: en ut-bygg-bar, lätt-användlig och egen-hostad plattform byggd för att köras helt offline. Anslut lokala modeller via Ollama eller använd OpenAI-kompatibla API'er för både lokala och molnbaserade modeller.</p>

[English](README.md) |
[简体中文](README.zh.md) |
[繁體中文](README.zht.md) |
[한국어](README.ko.md) |
[Deutsch](README.de.md) |
[Español](README.es.md) |
[Français](README.fr.md) |
[Italiano](README.it.md) |
[Dansk](README.da.md) |
[日本語](README.ja.md) |
[Polski](README.pl.md) |
[Русский](README.ru.md) |
[Bosanski](README.bs.md) |
[العربية](README.ar.md) |
[Norsk](README.no.md) |
[Português (Brasil)](README.br.md) |
[ไทย](README.th.md) |
[Türkçe](README.tr.md) |
[Українська](README.uk.md) |
[বাংলা](README.bn.md) |
[Ελληνικά](README.gr.md) |
[Tiếng Việt](README.vi.md) |
[Svenska](README.sv.md)

[![Open WebUI Demo](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stjärnor](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo storlek](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub antal nummer av språk](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top språk](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub senaste commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Utforska Open WebUI →](https://docs.openwebui.com/)

### Installation

#### Python

```bash
# Med uv installerat (macOS/Linux)
DATA_DIR=~/.open-webui uvx --python 3.12 open-webui@latest serve

# Eller installera och kör med pip (Python 3.12)
pip install open-webui
open-webui serve
```

Sedan öppna [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Sedan öppna [http://localhost:3000](http://localhost:3000).

| Bild tag | Inkluderar                                                                                 |
| --------- | ---------------------------------------------------------------------------------------- |
| `:main`   | Standard bild med lokala AI beroenden                                                |
| `:slim`   | Lightweight bild med externa servicer för embeddings, dokument extraction, och tal |
| `:cuda`   | Öppna WebUI med CUDA acceleration                                                        |
| `:ollama` | Öppna WebUI bundled med Ollama                                                           |
| `:dev`    | Senaste development bygg                                                                 |


Lägg till dessa flaggor till `docker run` innan bildens namn om det behövs:

| Option                                               | Purpose                                                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Anslut till Ollama på en annan server                                                      |
| `-e OPENAI_API_KEY=your_secret_key`                  | Sätt in din OpenAI API key                                                                  |
| `-e HF_HUB_OFFLINE=1`                                | Disablea Hugging Face model nedladdningar för att använda offline                                     |
| `--gpus all`                                         | Enablea Nvidia GPU åtkomst för `:cuda` eller `:ollama`; Du behöver Nvidia Container Toolkit |

Se [Docker installations guiden](https://docs.openwebui.com/getting-started/quick-start/) för setup-instruktioner, konfiguration flaggor och andra alternativ.

#### Desktop App

[Ladda ned native-desktop appen](https://github.com/open-webui/desktop) för macOS, Windows, och Linux.

[Läs dokumentation →](https://docs.openwebui.com/getting-started/)

### Ecosystem

- [Öppna Terminal](https://github.com/open-webui/open-terminal) / [Terminaler (Enterprise)](https://github.com/open-webui/terminals): Det aktivitets lager som gör Open WebUI till ett fullt "agent harness", med enterprise orchestration för pär-användare workspaces.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Spegla mappar, repos, buckets, och wikis i Open WebUI Knowledge Baser med inkrementell sync.
- [Open WebUI Computer](https://github.com/open-webui/computer): Din dator i vilken webbläsare som hellst: filer, editors, terminaler, git, och friviliga AI agenter, körs på ditt lokala system.

Se [ecosystemets dokumentation](https://docs.openwebui.com/ecosystem/) för detaljer.

### Troubleshooting and Updates

See the [troubleshooting guide](https://docs.openwebui.com/troubleshooting/) for connection issues and the [updating guide](https://docs.openwebui.com/getting-started/updating) to update your installation.

### Documentation

See the [docs](https://docs.openwebui.com/) for configuration and usage, and the [roadmap](https://docs.openwebui.com/roadmap/) for planned work.

For Docker Compose, Kubernetes, and other setups, see the [installation docs](https://docs.openwebui.com/getting-started/).

### Support

[Open an issue](https://github.com/open-webui/open-webui/issues) or [start a discussion](https://github.com/open-webui/open-webui/discussions).

Find us on [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI), and [Discord](https://discord.gg/5rJgQTnV4s).

### Security

Report vulnerabilities privately through [GitHub security advisories](https://github.com/open-webui/open-webui/security). Security reports are accepted only through GitHub.

### Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### License

Includes code under the Open WebUI License, which requires preserving the Open WebUI branding, and prior contributions under their original licenses. See [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) for terms and history.

[Enterprise](https://docs.openwebui.com/enterprise) · [Careers](https://careers.openwebui.com/) · [Sponsor](https://github.com/sponsors/open-webui)

Created by [Timothy Jaeryang Baek](https://github.com/tjbck).
