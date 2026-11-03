<h2>Open WebUI</h2>

<p>Open WebUI er <a href="https://docs.openwebui.com/"><strong>et hjem til AI</strong></a>: en udvidelig og brugervenlig platform, som du selv hoster, og som er bygget til at køre helt offline. Tilslut lokale modeller via Ollama, eller brug OpenAI-kompatible API’er til lokale modeller og cloudmodeller.</p>

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
[Tiếng Việt](README.vi.md)

[![Open WebUI-demonstration](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Udforsk Open WebUI →](https://docs.openwebui.com/)

### Installation

#### Python

Kræver Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Åbn derefter [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Åbn derefter [http://localhost:3000](http://localhost:3000).

| Image-tag | Indhold                                                                     |
| --------- | --------------------------------------------------------------------------- |
| `:main`   | Standardimage med afhængigheder til lokal AI                                |
| `:slim`   | Letvægtsimage med eksterne tjenester til embeddings, dokumentudtræk og tale |
| `:cuda`   | Open WebUI med CUDA-acceleration                                            |
| `:ollama` | Open WebUI med Ollama inkluderet                                            |
| `:dev`    | Nyeste udviklingsbuild                                                      |

Tilføj disse indstillinger til `docker run` før image-navnet efter behov:

| Indstilling                                          | Formål                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Opret forbindelse til Ollama på en anden server                                        |
| `-e OPENAI_API_KEY=your_secret_key`                  | Angiv din OpenAI-API-nøgle                                                             |
| `-e HF_HUB_OFFLINE=1`                                | Deaktiver download af Hugging Face-modeller til offlinebrug                            |
| `--gpus all`                                         | Aktiver Nvidia-GPU-adgang for `:cuda` eller `:ollama`; kræver Nvidia Container Toolkit |

Se [installationsvejledningen til Docker](https://docs.openwebui.com/getting-started/quick-start/) for opsætning og konfigurationsmuligheder.

#### Desktop-app

[Download den native desktop-app](https://github.com/open-webui/desktop) til macOS, Windows og Linux.

[Læs dokumentationen →](https://docs.openwebui.com/getting-started/)

### Økosystem

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Det eksekveringslag, der gør Open WebUI til et komplet agentmiljø, med enterprise-orkestrering af individuelle arbejdsområder til hver bruger.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Spejl mapper, repositories, buckets og wikier i Open WebUI Knowledge Bases med inkrementel synkronisering.
- [Open WebUI Computer](https://github.com/open-webui/computer): Din computer i enhver browser: filer, editor, terminal, Git og valgfrie AI-agenter, som kører på din egen maskine.

Se [dokumentationen til økosystemet](https://docs.openwebui.com/ecosystem/) for flere oplysninger.

### Fejlfinding og opdateringer

Se [fejlfindingsvejledningen](https://docs.openwebui.com/troubleshooting/) ved forbindelsesproblemer og [opdateringsvejledningen](https://docs.openwebui.com/getting-started/updating) for at opdatere din installation.

### Dokumentation

Se [dokumentationen](https://docs.openwebui.com/) for konfiguration og brug samt [køreplanen](https://docs.openwebui.com/roadmap/) for planlagt arbejde.

For Docker Compose, Kubernetes og andre opsætninger, se [installationsdokumentationen](https://docs.openwebui.com/getting-started/).

### Hjælp

[Opret et issue](https://github.com/open-webui/open-webui/issues), eller [start en diskussion](https://github.com/open-webui/open-webui/discussions).

Find os på [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) og [Discord](https://discord.gg/5rJgQTnV4s).

### Sikkerhed

Indberet sårbarheder fortroligt via [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Sikkerhedsrapporter modtages kun via GitHub.

### Stjernehistorik

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Diagram over stjernehistorik" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licens

Indeholder kode under Open WebUI License, som kræver, at Open WebUI-brandingen bevares, samt tidligere bidrag under deres oprindelige licenser. Se [LICENSE](./LICENSE) og [LICENSE_HISTORY](./LICENSE_HISTORY) for vilkår og historik.

[Enterprise](https://docs.openwebui.com/enterprise) · [Karriere](https://careers.openwebui.com/) · [Støt projektet](https://github.com/sponsors/open-webui)

Skabt af [Timothy Jaeryang Baek](https://github.com/tjbck).
