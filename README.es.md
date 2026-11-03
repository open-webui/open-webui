<h2>Open WebUI</h2>

<p>Open WebUI es <a href="https://docs.openwebui.com/"><strong>un hogar para la IA</strong></a>: una plataforma autoalojada, extensible y fácil de usar, diseñada para funcionar completamente sin conexión. Conecta modelos locales mediante Ollama o usa API compatibles con OpenAI para modelos locales y en la nube.</p>

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

[![Demostración de Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Explora Open WebUI →](https://docs.openwebui.com/)

### Instalación

#### Python

Requiere Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Después, abre [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Después, abre [http://localhost:3000](http://localhost:3000).

| Etiqueta de imagen | Contenido                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------- |
| `:main`            | Imagen estándar con dependencias de IA local                                             |
| `:slim`            | Imagen ligera que usa servicios externos para embeddings, extracción de documentos y voz |
| `:cuda`            | Open WebUI con aceleración CUDA                                                          |
| `:ollama`          | Open WebUI con Ollama incluido                                                           |
| `:dev`             | Última compilación de desarrollo                                                         |

Añade estas opciones a `docker run` antes del nombre de la imagen según lo necesites:

| Opción                                               | Función                                                                                      |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Conectarse a Ollama en otro servidor                                                         |
| `-e OPENAI_API_KEY=your_secret_key`                  | Configurar tu clave de API de OpenAI                                                         |
| `-e HF_HUB_OFFLINE=1`                                | Desactivar las descargas de modelos de Hugging Face para el uso sin conexión                 |
| `--gpus all`                                         | Habilitar el acceso a GPU Nvidia para `:cuda` o `:ollama`; requiere Nvidia Container Toolkit |

Consulta la [guía de instalación con Docker](https://docs.openwebui.com/getting-started/quick-start/) para ver las instrucciones y opciones de configuración.

#### Aplicación de escritorio

[Descarga la aplicación de escritorio nativa](https://github.com/open-webui/desktop) para macOS, Windows y Linux.

[Lee la documentación →](https://docs.openwebui.com/getting-started/)

### Ecosistema

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): La capa de ejecución que convierte Open WebUI en un entorno completo para agentes, con orquestación empresarial de espacios de trabajo por usuario.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Replica carpetas, repositorios, buckets y wikis en las bases de conocimiento de Open WebUI mediante sincronización incremental.
- [Open WebUI Computer](https://github.com/open-webui/computer): Tu ordenador en cualquier navegador: archivos, editor, terminal, Git y agentes de IA opcionales, ejecutándose en tu propia máquina.

Consulta la [documentación del ecosistema](https://docs.openwebui.com/ecosystem/) para más información.

### Resolución de problemas y actualizaciones

Consulta la [guía de resolución de problemas](https://docs.openwebui.com/troubleshooting/) para los problemas de conexión y la [guía de actualización](https://docs.openwebui.com/getting-started/updating) para actualizar tu instalación.

### Documentación

Consulta la [documentación](https://docs.openwebui.com/) para la configuración y el uso, y la [hoja de ruta](https://docs.openwebui.com/roadmap/) para el trabajo previsto.

Para Docker Compose, Kubernetes y otras instalaciones, consulta la [documentación de instalación](https://docs.openwebui.com/getting-started/).

### Ayuda

[Abre una incidencia](https://github.com/open-webui/open-webui/issues) o [inicia una discusión](https://github.com/open-webui/open-webui/discussions).

Encuéntranos en [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) y [Discord](https://discord.gg/5rJgQTnV4s).

### Seguridad

Comunica vulnerabilidades de forma privada mediante [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Solo se aceptan informes de seguridad a través de GitHub.

### Historial de estrellas

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Gráfico del historial de estrellas" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licencia

Incluye código bajo la Open WebUI License, que exige conservar la marca Open WebUI, y contribuciones anteriores bajo sus licencias originales. Consulta [LICENSE](./LICENSE) y [LICENSE_HISTORY](./LICENSE_HISTORY) para conocer las condiciones y el historial.

[Empresas](https://docs.openwebui.com/enterprise) · [Empleo](https://careers.openwebui.com/) · [Patrocinar](https://github.com/sponsors/open-webui)

Creado por [Timothy Jaeryang Baek](https://github.com/tjbck).
