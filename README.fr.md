<h2>Open WebUI</h2>

<p>Open WebUI est <a href="https://docs.openwebui.com/"><strong>un foyer pour l’IA</strong></a> : une plateforme auto-hébergée, extensible et facile à utiliser, conçue pour fonctionner entièrement hors ligne. Connectez des modèles locaux via Ollama ou utilisez des API compatibles avec OpenAI pour des modèles locaux et cloud.</p>

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

[![Démonstration d’Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Découvrir Open WebUI →](https://docs.openwebui.com/)

### Installation

#### Python

Nécessite Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Ouvrez ensuite [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Ouvrez ensuite [http://localhost:3000](http://localhost:3000).

| Tag de l’image | Contenu                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| `:main`        | Image standard avec les dépendances d’IA locales                                                       |
| `:slim`        | Image légère utilisant des services externes pour les embeddings, l’extraction de documents et la voix |
| `:cuda`        | Open WebUI avec accélération CUDA                                                                      |
| `:ollama`      | Open WebUI avec Ollama intégré                                                                         |
| `:dev`         | Dernière version de développement                                                                      |

Ajoutez ces options à `docker run` avant le nom de l’image, selon vos besoins :

| Option                                               | Fonction                                                                                      |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Se connecter à Ollama sur un autre serveur                                                    |
| `-e OPENAI_API_KEY=your_secret_key`                  | Définir votre clé API OpenAI                                                                  |
| `-e HF_HUB_OFFLINE=1`                                | Désactiver le téléchargement des modèles Hugging Face pour une utilisation hors ligne         |
| `--gpus all`                                         | Activer l’accès aux GPU Nvidia pour `:cuda` ou `:ollama` ; nécessite Nvidia Container Toolkit |

Consultez le [guide d’installation Docker](https://docs.openwebui.com/getting-started/quick-start/) pour les instructions et les options de configuration.

#### Application de bureau

[Téléchargez l’application de bureau native](https://github.com/open-webui/desktop) pour macOS, Windows et Linux.

[Lire la documentation →](https://docs.openwebui.com/getting-started/)

### Écosystème

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): La couche d’exécution qui fait d’Open WebUI un environnement complet pour les agents, avec une orchestration d’entreprise des espaces de travail individuels.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Répliquez dossiers, dépôts, buckets et wikis dans les bases de connaissances Open WebUI grâce à la synchronisation incrémentale.
- [Open WebUI Computer](https://github.com/open-webui/computer): Votre ordinateur dans n’importe quel navigateur : fichiers, éditeur, terminal, Git et agents IA facultatifs, exécutés sur votre propre machine.

Consultez la [documentation de l’écosystème](https://docs.openwebui.com/ecosystem/) pour en savoir plus.

### Dépannage et mises à jour

Consultez le [guide de dépannage](https://docs.openwebui.com/troubleshooting/) pour les problèmes de connexion et le [guide de mise à jour](https://docs.openwebui.com/getting-started/updating) pour actualiser votre installation.

### Documentation

Consultez la [documentation](https://docs.openwebui.com/) pour la configuration et l’utilisation, et la [feuille de route](https://docs.openwebui.com/roadmap/) pour les travaux prévus.

Pour Docker Compose, Kubernetes et les autres modes d’installation, consultez la [documentation d’installation](https://docs.openwebui.com/getting-started/).

### Assistance

[Ouvrez une issue](https://github.com/open-webui/open-webui/issues) ou [lancez une discussion](https://github.com/open-webui/open-webui/discussions).

Retrouvez-nous sur [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) et [Discord](https://discord.gg/5rJgQTnV4s).

### Sécurité

Signalez les vulnérabilités de manière confidentielle via [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Les signalements de sécurité sont acceptés uniquement sur GitHub.

### Historique des étoiles

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Graphique de l’historique des étoiles" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licence

Inclut du code sous Open WebUI License, qui impose de conserver l’identité de marque Open WebUI, ainsi que des contributions antérieures sous leurs licences d’origine. Consultez [LICENSE](./LICENSE) et [LICENSE_HISTORY](./LICENSE_HISTORY) pour les conditions et l’historique.

[Entreprise](https://docs.openwebui.com/enterprise) · [Carrières](https://careers.openwebui.com/) · [Soutenir](https://github.com/sponsors/open-webui)

Créé par [Timothy Jaeryang Baek](https://github.com/tjbck).
