<h2>Open WebUI</h2>

<p>Open WebUI è <a href="https://docs.openwebui.com/"><strong>una casa per l’IA</strong></a>: una piattaforma self-hosted, estensibile e facile da usare, progettata per funzionare completamente offline. Collega modelli locali tramite Ollama oppure usa API compatibili con OpenAI per modelli locali e cloud.</p>

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

[![Demo di Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Esplora Open WebUI →](https://docs.openwebui.com/)

### Installazione

#### Python

Richiede Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Poi apri [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Poi apri [http://localhost:3000](http://localhost:3000).

| Tag dell’immagine | Contenuto                                                                               |
| ----------------- | --------------------------------------------------------------------------------------- |
| `:main`           | Immagine standard con dipendenze per l’IA locale                                        |
| `:slim`           | Immagine leggera che usa servizi esterni per embedding, estrazione dei documenti e voce |
| `:cuda`           | Open WebUI con accelerazione CUDA                                                       |
| `:ollama`         | Open WebUI con Ollama incluso                                                           |
| `:dev`            | Ultima build di sviluppo                                                                |

Aggiungi queste opzioni a `docker run` prima del nome dell’immagine, secondo necessità:

| Opzione                                              | Scopo                                                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Collegarsi a Ollama su un altro server                                                         |
| `-e OPENAI_API_KEY=your_secret_key`                  | Impostare la chiave API OpenAI                                                                 |
| `-e HF_HUB_OFFLINE=1`                                | Disabilitare i download dei modelli Hugging Face per l’uso offline                             |
| `--gpus all`                                         | Abilitare l’accesso alla GPU Nvidia per `:cuda` o `:ollama`; richiede Nvidia Container Toolkit |

Consulta la [guida all’installazione con Docker](https://docs.openwebui.com/getting-started/quick-start/) per le istruzioni e le opzioni di configurazione.

#### App desktop

[Scarica l’app desktop nativa](https://github.com/open-webui/desktop) per macOS, Windows e Linux.

[Leggi la documentazione →](https://docs.openwebui.com/getting-started/)

### Ecosistema

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Il livello di esecuzione che rende Open WebUI un ambiente completo per gli agenti, con orchestrazione enterprise degli spazi di lavoro per utente.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Replica cartelle, repository, bucket e wiki nelle basi di conoscenza di Open WebUI tramite sincronizzazione incrementale.
- [Open WebUI Computer](https://github.com/open-webui/computer): Il tuo computer in qualsiasi browser: file, editor, terminale, Git e agenti IA facoltativi, in esecuzione sulla tua macchina.

Consulta la [documentazione dell’ecosistema](https://docs.openwebui.com/ecosystem/) per i dettagli.

### Risoluzione dei problemi e aggiornamenti

Consulta la [guida alla risoluzione dei problemi](https://docs.openwebui.com/troubleshooting/) per i problemi di connessione e la [guida agli aggiornamenti](https://docs.openwebui.com/getting-started/updating) per aggiornare l’installazione.

### Documentazione

Consulta la [documentazione](https://docs.openwebui.com/) per configurazione e utilizzo, e la [roadmap](https://docs.openwebui.com/roadmap/) per il lavoro previsto.

Per Docker Compose, Kubernetes e altre installazioni, consulta la [documentazione di installazione](https://docs.openwebui.com/getting-started/).

### Supporto

[Apri una segnalazione](https://github.com/open-webui/open-webui/issues) oppure [avvia una discussione](https://github.com/open-webui/open-webui/discussions).

Ci trovi su [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) e [Discord](https://discord.gg/5rJgQTnV4s).

### Sicurezza

Segnala le vulnerabilità in privato tramite [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Le segnalazioni di sicurezza sono accettate solo tramite GitHub.

### Cronologia delle stelle

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Grafico della cronologia delle stelle" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licenza

Include codice soggetto alla Open WebUI License, che richiede di mantenere il marchio Open WebUI, e contributi precedenti soggetti alle rispettive licenze originali. Consulta [LICENSE](./LICENSE) e [LICENSE_HISTORY](./LICENSE_HISTORY) per condizioni e cronologia.

[Enterprise](https://docs.openwebui.com/enterprise) · [Lavora con noi](https://careers.openwebui.com/) · [Sostieni](https://github.com/sponsors/open-webui)

Creato da [Timothy Jaeryang Baek](https://github.com/tjbck).
