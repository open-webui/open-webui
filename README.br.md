<h2>Open WebUI</h2>

<p>Open WebUI é <a href="https://docs.openwebui.com/"><strong>um lar para a IA</strong></a>: uma plataforma auto-hospedada, extensível e fácil de usar, feita para funcionar totalmente offline. Conecte modelos locais pelo Ollama ou use APIs compatíveis com OpenAI para modelos locais e na nuvem.</p>

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

[![Demonstração do Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Explore o Open WebUI →](https://docs.openwebui.com/)

### Instalação

#### Python

Requer Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Depois, abra [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Depois, abra [http://localhost:3000](http://localhost:3000).

| Tag da imagem | Conteúdo                                                                            |
| ------------- | ----------------------------------------------------------------------------------- |
| `:main`       | Imagem padrão com dependências de IA local                                          |
| `:slim`       | Imagem leve que usa serviços externos para embeddings, extração de documentos e voz |
| `:cuda`       | Open WebUI com aceleração CUDA                                                      |
| `:ollama`     | Open WebUI com Ollama incluído                                                      |
| `:dev`        | Build de desenvolvimento mais recente                                               |

Adicione estas opções ao `docker run` antes do nome da imagem, conforme necessário:

| Opção                                                | Finalidade                                                                                 |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Conectar ao Ollama em outro servidor                                                       |
| `-e OPENAI_API_KEY=your_secret_key`                  | Definir sua chave de API da OpenAI                                                         |
| `-e HF_HUB_OFFLINE=1`                                | Desativar downloads de modelos do Hugging Face para uso offline                            |
| `--gpus all`                                         | Habilitar acesso à GPU Nvidia para `:cuda` ou `:ollama`; requer o Nvidia Container Toolkit |

Consulte o [guia de instalação com Docker](https://docs.openwebui.com/getting-started/quick-start/) para instruções e opções de configuração.

#### Aplicativo para desktop

[Baixe o aplicativo nativo para desktop](https://github.com/open-webui/desktop) para macOS, Windows e Linux.

[Leia a documentação →](https://docs.openwebui.com/getting-started/)

### Ecossistema

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): A camada de execução que transforma o Open WebUI em um ambiente completo para agentes, com orquestração empresarial de espaços de trabalho por usuário.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Espelhe pastas, repositórios, buckets e wikis nas bases de conhecimento do Open WebUI com sincronização incremental.
- [Open WebUI Computer](https://github.com/open-webui/computer): Seu computador em qualquer navegador: arquivos, editor, terminal, Git e agentes de IA opcionais, executados na sua própria máquina.

Consulte a [documentação do ecossistema](https://docs.openwebui.com/ecosystem/) para mais detalhes.

### Solução de problemas e atualizações

Consulte o [guia de solução de problemas](https://docs.openwebui.com/troubleshooting/) para problemas de conexão e o [guia de atualização](https://docs.openwebui.com/getting-started/updating) para atualizar sua instalação.

### Documentação

Consulte a [documentação](https://docs.openwebui.com/) para configuração e uso, e o [roteiro](https://docs.openwebui.com/roadmap/) para o trabalho planejado.

Para Docker Compose, Kubernetes e outras formas de instalação, consulte a [documentação de instalação](https://docs.openwebui.com/getting-started/).

### Suporte

[Abra uma issue](https://github.com/open-webui/open-webui/issues) ou [inicie uma discussão](https://github.com/open-webui/open-webui/discussions).

Encontre-nos no [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) e [Discord](https://discord.gg/5rJgQTnV4s).

### Segurança

Relate vulnerabilidades de forma privada pelo [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Relatos de segurança são aceitos somente pelo GitHub.

### Histórico de estrelas

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Gráfico do histórico de estrelas" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Licença

Inclui código sob a Open WebUI License, que exige preservar a marca Open WebUI, e contribuições anteriores sob suas licenças originais. Consulte [LICENSE](./LICENSE) e [LICENSE_HISTORY](./LICENSE_HISTORY) para os termos e o histórico.

[Empresas](https://docs.openwebui.com/enterprise) · [Carreiras](https://careers.openwebui.com/) · [Patrocine](https://github.com/sponsors/open-webui)

Criado por [Timothy Jaeryang Baek](https://github.com/tjbck).
