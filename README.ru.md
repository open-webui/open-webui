<h2>Open WebUI</h2>

<p>Open WebUI — это <a href="https://docs.openwebui.com/"><strong>дом для ИИ</strong></a>: расширяемая и удобная платформа для самостоятельного размещения, способная работать полностью офлайн. Подключайте локальные модели через Ollama или используйте совместимые с OpenAI API для локальных и облачных моделей.</p>

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

[![Демонстрация Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Знакомство с Open WebUI →](https://docs.openwebui.com/)

### Установка

#### Python

Требуется Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Затем откройте [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Затем откройте [http://localhost:3000](http://localhost:3000).

| Тег образа | Содержимое |
| --- | --- |
| `:main` | Стандартный образ с зависимостями для локального ИИ |
| `:slim` | Облегчённый образ с внешними сервисами для эмбеддингов, извлечения данных из документов и обработки речи |
| `:cuda` | Open WebUI с ускорением CUDA |
| `:ollama` | Open WebUI со встроенным Ollama |
| `:dev` | Последняя сборка для разработки |

При необходимости добавьте эти параметры в `docker run` перед именем образа:

| Параметр | Назначение |
| --- | --- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Подключение к Ollama на другом сервере |
| `-e OPENAI_API_KEY=your_secret_key` | Установка ключа API OpenAI |
| `-e HF_HUB_OFFLINE=1` | Отключение загрузки моделей Hugging Face для работы офлайн |
| `--gpus all` | Доступ к GPU Nvidia для `:cuda` или `:ollama`; требуется Nvidia Container Toolkit |

Инструкции и параметры настройки приведены в [руководстве по установке через Docker](https://docs.openwebui.com/getting-started/quick-start/).

#### Приложение для компьютера

[Скачайте нативное приложение](https://github.com/open-webui/desktop) для macOS, Windows и Linux.

[Читать документацию →](https://docs.openwebui.com/getting-started/)

### Экосистема

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Слой выполнения действий, который превращает Open WebUI в полноценную среду для агентов, с корпоративной оркестрацией отдельных рабочих пространств пользователей.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Зеркалирование папок, репозиториев, бакетов и вики в базы знаний Open WebUI с инкрементальной синхронизацией.
- [Open WebUI Computer](https://github.com/open-webui/computer): Ваш компьютер в любом браузере: файлы, редактор, терминал, Git и необязательные ИИ-агенты, работающие на вашей реальной машине.

Подробнее — в [документации экосистемы](https://docs.openwebui.com/ecosystem/).

### Устранение неполадок и обновления

При проблемах с подключением обратитесь к [руководству по устранению неполадок](https://docs.openwebui.com/troubleshooting/), а для обновления установки — к [руководству по обновлению](https://docs.openwebui.com/getting-started/updating).

### Документация

Настройка и использование описаны в [документации](https://docs.openwebui.com/), а запланированные работы — в [дорожной карте](https://docs.openwebui.com/roadmap/).

Для Docker Compose, Kubernetes и других вариантов установки см. [документацию по установке](https://docs.openwebui.com/getting-started/).

### Поддержка

[Создайте issue](https://github.com/open-webui/open-webui/issues) или [начните обсуждение](https://github.com/open-webui/open-webui/discussions).

Мы есть на [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) и [Discord](https://discord.gg/5rJgQTnV4s).

### Безопасность

Сообщайте об уязвимостях конфиденциально через [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Сообщения о безопасности принимаются только через GitHub.

### История звёзд

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="График истории звёзд" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Лицензия

Включает код под Open WebUI License, которая требует сохранения брендинга Open WebUI, а также предыдущие вклады под их исходными лицензиями. Условия и история приведены в [LICENSE](./LICENSE) и [LICENSE_HISTORY](./LICENSE_HISTORY).

[Для организаций](https://docs.openwebui.com/enterprise) · [Карьера](https://careers.openwebui.com/) · [Поддержать проект](https://github.com/sponsors/open-webui)

Автор: [Timothy Jaeryang Baek](https://github.com/tjbck).
