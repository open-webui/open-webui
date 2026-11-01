<h2>Open WebUI</h2>

<p>Open WebUI — це <a href="https://docs.openwebui.com/"><strong>дім для ШІ</strong></a>: розширювана й зручна платформа для самостійного розгортання, здатна працювати повністю офлайн. Підключайте локальні моделі через Ollama або використовуйте сумісні з OpenAI API для локальних і хмарних моделей.</p>

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

[![Демонстрація Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Дізнатися про Open WebUI →](https://docs.openwebui.com/)

### Встановлення

#### Python

Потрібен Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Потім відкрийте [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Потім відкрийте [http://localhost:3000](http://localhost:3000).

| Тег образу | Вміст |
| --- | --- |
| `:main` | Стандартний образ із залежностями для локального ШІ |
| `:slim` | Полегшений образ із зовнішніми сервісами для ембедингів, видобування даних із документів і обробки мовлення |
| `:cuda` | Open WebUI з прискоренням CUDA |
| `:ollama` | Open WebUI із вбудованим Ollama |
| `:dev` | Найновіша збірка для розробки |

За потреби додайте ці параметри до `docker run` перед назвою образу:

| Параметр | Призначення |
| --- | --- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Підключення до Ollama на іншому сервері |
| `-e OPENAI_API_KEY=your_secret_key` | Встановлення ключа API OpenAI |
| `-e HF_HUB_OFFLINE=1` | Вимкнення завантаження моделей Hugging Face для роботи офлайн |
| `--gpus all` | Доступ до GPU Nvidia для `:cuda` або `:ollama`; потрібен Nvidia Container Toolkit |

Інструкції та параметри налаштування наведено в [посібнику зі встановлення через Docker](https://docs.openwebui.com/getting-started/quick-start/).

#### Настільний застосунок

[Завантажте нативний настільний застосунок](https://github.com/open-webui/desktop) для macOS, Windows і Linux.

[Читати документацію →](https://docs.openwebui.com/getting-started/)

### Екосистема

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Шар виконання дій, який перетворює Open WebUI на повноцінне середовище для агентів, із корпоративною оркестрацією окремих робочих просторів користувачів.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Дзеркальне копіювання папок, репозиторіїв, бакетів і вікі до баз знань Open WebUI з інкрементальною синхронізацією.
- [Open WebUI Computer](https://github.com/open-webui/computer): Ваш комп’ютер у будь-якому браузері: файли, редактор, термінал, Git і необов’язкові ШІ-агенти, що працюють на вашій реальній машині.

Докладніше — у [документації екосистеми](https://docs.openwebui.com/ecosystem/).

### Усунення несправностей та оновлення

У разі проблем із підключенням дивіться [посібник з усунення несправностей](https://docs.openwebui.com/troubleshooting/), а для оновлення інсталяції — [посібник з оновлення](https://docs.openwebui.com/getting-started/updating).

### Документація

Налаштування й використання описано в [документації](https://docs.openwebui.com/), а заплановані роботи — у [дорожній карті](https://docs.openwebui.com/roadmap/).

Для Docker Compose, Kubernetes та інших способів встановлення дивіться [документацію зі встановлення](https://docs.openwebui.com/getting-started/).

### Підтримка

[Створіть issue](https://github.com/open-webui/open-webui/issues) або [розпочніть обговорення](https://github.com/open-webui/open-webui/discussions).

Знайдіть нас на [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) і [Discord](https://discord.gg/5rJgQTnV4s).

### Безпека

Повідомляйте про вразливості конфіденційно через [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Повідомлення про безпеку приймаються лише через GitHub.

### Історія зірок

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Графік історії зірок" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Ліцензія

Містить код під Open WebUI License, яка вимагає збереження брендингу Open WebUI, а також попередні внески під їхніми початковими ліцензіями. Умови й історію наведено в [LICENSE](./LICENSE) та [LICENSE_HISTORY](./LICENSE_HISTORY).

[Для організацій](https://docs.openwebui.com/enterprise) · [Кар’єра](https://careers.openwebui.com/) · [Підтримати проєкт](https://github.com/sponsors/open-webui)

Автор: [Timothy Jaeryang Baek](https://github.com/tjbck).
