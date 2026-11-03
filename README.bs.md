<h2>Open WebUI</h2>

<p>Open WebUI je <a href="https://docs.openwebui.com/"><strong>dom za AI</strong></a>: proširiva platforma jednostavna za korištenje, koju sami hostujete i koja može raditi potpuno offline. Povežite lokalne modele putem Ollame ili koristite API-je kompatibilne s OpenAI-jem za lokalne modele i modele u oblaku.</p>

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

[![Demonstracija Open WebUI-ja](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Istražite Open WebUI →](https://docs.openwebui.com/)

### Instalacija

#### Python

Potreban je Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Zatim otvorite [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Zatim otvorite [http://localhost:3000](http://localhost:3000).

| Oznaka slike | Sadržaj                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------- |
| `:main`      | Standardna slika sa zavisnostima za lokalni AI                                                  |
| `:slim`      | Lagana slika koja koristi vanjske servise za embeddinge, izdvajanje sadržaja dokumenata i govor |
| `:cuda`      | Open WebUI s CUDA ubrzanjem                                                                     |
| `:ollama`    | Open WebUI s uključenom Ollamom                                                                 |
| `:dev`       | Najnovija razvojna verzija                                                                      |

Po potrebi dodajte ove opcije u `docker run` prije naziva slike:

| Opcija                                               | Namjena                                                                                           |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Povezivanje s Ollamom na drugom serveru                                                           |
| `-e OPENAI_API_KEY=your_secret_key`                  | Postavljanje OpenAI API ključa                                                                    |
| `-e HF_HUB_OFFLINE=1`                                | Isključivanje preuzimanja Hugging Face modela za rad offline                                      |
| `--gpus all`                                         | Omogućavanje pristupa Nvidia GPU-u za `:cuda` ili `:ollama`; potreban je Nvidia Container Toolkit |

Upute i opcije konfiguracije nalaze se u [vodiču za instalaciju putem Dockera](https://docs.openwebui.com/getting-started/quick-start/).

#### Desktop aplikacija

[Preuzmite nativnu desktop aplikaciju](https://github.com/open-webui/desktop) za macOS, Windows i Linux.

[Pročitajte dokumentaciju →](https://docs.openwebui.com/getting-started/)

### Ekosistem

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Izvršni sloj koji pretvara Open WebUI u potpuno okruženje za agente, s poslovnom orkestracijom zasebnih radnih prostora za svakog korisnika.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Preslikajte foldere, repozitorije, spremnike i wikije u baze znanja Open WebUI-ja uz inkrementalnu sinhronizaciju.
- [Open WebUI Computer](https://github.com/open-webui/computer): Vaš računar u bilo kojem pregledniku: datoteke, uređivač, terminal, Git i opcionalni AI agenti koji rade na vašem stvarnom računaru.

Detalje potražite u [dokumentaciji ekosistema](https://docs.openwebui.com/ecosystem/).

### Rješavanje problema i ažuriranja

Za probleme s povezivanjem pogledajte [vodič za rješavanje problema](https://docs.openwebui.com/troubleshooting/), a za ažuriranje instalacije [vodič za ažuriranje](https://docs.openwebui.com/getting-started/updating).

### Dokumentacija

Za konfiguraciju i korištenje pogledajte [dokumentaciju](https://docs.openwebui.com/), a za planirani rad [plan razvoja](https://docs.openwebui.com/roadmap/).

Za Docker Compose, Kubernetes i druge načine instalacije pogledajte [dokumentaciju za instalaciju](https://docs.openwebui.com/getting-started/).

### Podrška

[Otvorite prijavu](https://github.com/open-webui/open-webui/issues) ili [pokrenite raspravu](https://github.com/open-webui/open-webui/discussions).

Pronađite nas na [Redditu](https://www.reddit.com/r/OpenWebUI/), [X-u](https://x.com/OpenWebUI) i [Discordu](https://discord.gg/5rJgQTnV4s).

### Sigurnost

Ranjivosti prijavite privatno putem [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Sigurnosne prijave prihvatamo isključivo putem GitHuba.

### Historija zvjezdica

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Grafikon historije zvjezdica" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licenca

Sadrži kod pod licencom Open WebUI License, koja zahtijeva očuvanje brenda Open WebUI, te ranije doprinose pod njihovim izvornim licencama. Uslove i historiju pogledajte u [LICENSE](./LICENSE) i [LICENSE_HISTORY](./LICENSE_HISTORY).

[Enterprise](https://docs.openwebui.com/enterprise) · [Karijere](https://careers.openwebui.com/) · [Sponzorišite](https://github.com/sponsors/open-webui)

Autor: [Timothy Jaeryang Baek](https://github.com/tjbck).
