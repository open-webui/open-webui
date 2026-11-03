<h2>Open WebUI</h2>

<p>Open WebUI to <a href="https://docs.openwebui.com/"><strong>dom dla AI</strong></a>: rozszerzalna, łatwa w obsłudze platforma do samodzielnego hostowania, zaprojektowana do pracy całkowicie offline. Podłącz lokalne modele przez Ollama lub korzystaj z API zgodnych z OpenAI dla modeli lokalnych i chmurowych.</p>

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

[![Prezentacja Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Poznaj Open WebUI →](https://docs.openwebui.com/)

### Instalacja

#### Python

Wymaga Pythona 3.12.

```bash
pip install open-webui
open-webui serve
```

Następnie otwórz [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Następnie otwórz [http://localhost:3000](http://localhost:3000).

| Tag obrazu | Zawartość                                                                                       |
| ---------- | ----------------------------------------------------------------------------------------------- |
| `:main`    | Standardowy obraz z zależnościami dla lokalnej AI                                               |
| `:slim`    | Lekki obraz korzystający z usług zewnętrznych do osadzeń, ekstrakcji dokumentów i obsługi głosu |
| `:cuda`    | Open WebUI z akceleracją CUDA                                                                   |
| `:ollama`  | Open WebUI z dołączonym Ollama                                                                  |
| `:dev`     | Najnowsza kompilacja rozwojowa                                                                  |

W razie potrzeby dodaj te opcje do `docker run` przed nazwą obrazu:

| Opcja                                                | Zastosowanie                                                                               |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Połączenie z Ollama na innym serwerze                                                      |
| `-e OPENAI_API_KEY=your_secret_key`                  | Ustawienie klucza API OpenAI                                                               |
| `-e HF_HUB_OFFLINE=1`                                | Wyłączenie pobierania modeli Hugging Face do pracy offline                                 |
| `--gpus all`                                         | Włączenie dostępu do GPU Nvidia dla `:cuda` lub `:ollama`; wymaga Nvidia Container Toolkit |

Instrukcje i opcje konfiguracji znajdziesz w [przewodniku instalacji przez Docker](https://docs.openwebui.com/getting-started/quick-start/).

#### Aplikacja desktopowa

[Pobierz natywną aplikację desktopową](https://github.com/open-webui/desktop) dla macOS, Windows i Linux.

[Przeczytaj dokumentację →](https://docs.openwebui.com/getting-started/)

### Ekosystem

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Warstwa wykonawcza, która zmienia Open WebUI w kompletne środowisko agentowe, z orkiestracją klasy enterprise dla osobnych przestrzeni roboczych użytkowników.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Synchronizuj przyrostowo foldery, repozytoria, zasobniki i wiki z bazami wiedzy Open WebUI.
- [Open WebUI Computer](https://github.com/open-webui/computer): Twój komputer w dowolnej przeglądarce: pliki, edytor, terminal, Git i opcjonalni agenci AI, działający na twojej własnej maszynie.

Szczegóły znajdziesz w [dokumentacji ekosystemu](https://docs.openwebui.com/ecosystem/).

### Rozwiązywanie problemów i aktualizacje

W razie problemów z połączeniem skorzystaj z [poradnika rozwiązywania problemów](https://docs.openwebui.com/troubleshooting/), a aby zaktualizować instalację — z [poradnika aktualizacji](https://docs.openwebui.com/getting-started/updating).

### Dokumentacja

Informacje o konfiguracji i użytkowaniu znajdziesz w [dokumentacji](https://docs.openwebui.com/), a planowane prace w [planie rozwoju](https://docs.openwebui.com/roadmap/).

Informacje o Docker Compose, Kubernetes i innych sposobach instalacji znajdziesz w [dokumentacji instalacji](https://docs.openwebui.com/getting-started/).

### Pomoc

[Utwórz zgłoszenie](https://github.com/open-webui/open-webui/issues) lub [rozpocznij dyskusję](https://github.com/open-webui/open-webui/discussions).

Znajdziesz nas na [Reddicie](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) i [Discordzie](https://discord.gg/5rJgQTnV4s).

### Bezpieczeństwo

Zgłaszaj luki poufnie przez [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Zgłoszenia dotyczące bezpieczeństwa przyjmujemy wyłącznie przez GitHub.

### Historia gwiazdek

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Wykres historii gwiazdek" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licencja

Zawiera kod na licencji Open WebUI License, która wymaga zachowania oznaczeń marki Open WebUI, oraz wcześniejsze wkłady na ich oryginalnych licencjach. Warunki i historię znajdziesz w [LICENSE](./LICENSE) i [LICENSE_HISTORY](./LICENSE_HISTORY).

[Enterprise](https://docs.openwebui.com/enterprise) · [Kariera](https://careers.openwebui.com/) · [Wesprzyj](https://github.com/sponsors/open-webui)

Autor: [Timothy Jaeryang Baek](https://github.com/tjbck).
