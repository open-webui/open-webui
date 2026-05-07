# Reengenharia — Compreensão e Customização de Projetos Open-Source

## Objetivo

Documentar a abordagem usada para entender a arquitetura de um projeto open-source complexo **antes** de iniciar qualquer customização. O processo produz artefatos de referência reutilizáveis e reduz o risco de customizações que quebrem partes não mapeadas do sistema.

Este documento serve tanto como guia de processo (reutilizável em outros projetos) quanto como ponto de entrada para o estado atual do mapeamento do **open-webui-custom**.

---

## Metodologia

### Princípio central

> Ler antes de escrever. Mapear antes de modificar.

A customização sem compreensão gera débito técnico invisível — mudanças que funcionam localmente mas quebram ao atualizar o fork, ou que duplicam lógica já existente no projeto original.

### Roteiro de leitura (ordem recomendada)

| Etapa | O que ler | Por quê |
|-------|-----------|---------|
| 1 | `backend/open_webui/main.py` | Entry point: rotas montadas, middlewares, estado global da app |
| 2 | `backend/open_webui/routers/` | Endpoints por domínio — o contrato da API |
| 3 | `backend/open_webui/models/` | Schema de dados — o que persiste e como |
| 4 | `backend/open_webui/utils/` | Lógica de negócio transversal (auth, chat, middleware) |
| 5 | `backend/open_webui/internal/` | Banco de dados e migrations (Alembic) |
| 6 | `backend/open_webui/retrieval/` | Pipeline RAG — loaders, vector stores |
| 7 | `src/lib/stores/` | State management do frontend (Svelte stores) |
| 8 | `src/lib/components/` | Componentes UI por área funcional |
| 9 | `docker-compose.yaml` + `Dockerfile` | Dependências de infraestrutura |

### Artefatos produzidos nesta pasta

```
docs/reengenharia/
├── README.md               ← este arquivo (processo + mapa inicial)
├── arquitetura.md          ← diagrama detalhado de componentes e fluxos
├── dominios.md             ← mapeamento de domínios de negócio
├── api-surface.md          ← inventário de endpoints e responsabilidades
├── customizacoes.md        ← registro de onde e por que tocamos no código
└── decisoes.md             ← ADRs de customização (o que mudamos e por quê)
```

---

## Mapa Inicial de Arquitetura — open-webui

> Estado: mapeamento inicial a partir da leitura de estrutura de arquivos e `main.py`.  
> Data: 2026-05-06

### Visão geral

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER / CLIENT                    │
│              SvelteKit (src/)                           │
│   components/  ·  stores/  ·  utils/  ·  i18n/        │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP + WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                  FastAPI (backend/)                      │
│                                                         │
│  ┌─── Middleware ───────────────────────────────────┐   │
│  │  CORS · Session · Audit · Security Headers       │   │
│  │  process_chat_payload / process_chat_response    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─── Routers (API REST) ───────────────────────────┐   │
│  │  /ollama        /openai       /api/v1/pipelines  │   │
│  │  /api/v1/auths  /api/v1/users /api/v1/groups     │   │
│  │  /api/v1/chats  /api/v1/channels  /api/v1/models │   │
│  │  /api/v1/knowledge  /api/v1/retrieval            │   │
│  │  /api/v1/prompts    /api/v1/tools                │   │
│  │  /api/v1/functions  /api/v1/memories             │   │
│  │  /api/v1/files  /api/v1/folders                  │   │
│  │  /api/v1/images /api/v1/audio  /api/v1/tasks     │   │
│  │  /api/v1/configs  /api/v1/utils                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─── WebSocket ───┐  ┌─── Utils (negócio) ─────────┐  │
│  │  /ws (Socket.IO)│  │  auth · chat · middleware    │  │
│  │  real-time msgs │  │  oauth · webhook · plugin    │  │
│  └─────────────────┘  └────────────────────────────-─┘  │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
┌───────────▼──────┐      ┌───────────▼───────────────────┐
│  Banco Relacional │      │  Pipeline RAG                 │
│  SQLite / Postgres│      │                               │
│  (Alembic)        │      │  Loaders: main, mistral,      │
│                   │      │           tavily, youtube      │
│  models/          │      │                               │
│  auths · chats    │      │  Vector DBs (plugável):        │
│  users · files    │      │  Chroma · Milvus · Qdrant     │
│  knowledge · tools│      │  pgvector · Elasticsearch     │
│  functions · ...  │      │  OpenSearch                   │
└───────────────────┘      └───────────────────────────────┘
```

### Domínios de negócio (mapeamento rápido)

| Domínio | Routers | Models |
|---------|---------|--------|
| Identidade | auths, users, groups | auths, users, groups |
| Conversas | chats, channels | chats, messages, channels, tags |
| LLMs | ollama, openai, models, pipelines | models |
| Conhecimento | knowledge, retrieval, files, folders | knowledge, files, folders |
| Customização | prompts, tools, functions | prompts, tools, functions |
| Memória | memories | memories |
| Mídia | images, audio | files |
| Avaliação | evaluations | feedbacks |
| Admin | configs | — (estado em `app.state`) |

### Stack tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Frontend | SvelteKit + TypeScript + TailwindCSS |
| Backend | FastAPI + Python |
| ORM | SQLAlchemy + Alembic |
| Real-time | Socket.IO |
| RAG | Langchain-style loaders + vector DB plugável |
| Container | Docker + docker-compose |
| Auth | JWT + OAuth2 (Google, GitHub, etc.) |
| Storage | Local filesystem ou S3-compatible |

### Pontos de extensão (onde customizar com menor risco)

| Ponto | Localização | Tipo de mudança |
|-------|-------------|-----------------|
| Novo router/endpoint | `routers/` + registro em `main.py` | Adição |
| Nova model/tabela | `models/` + migration Alembic | Adição |
| Lógica de chat pré/pós | `utils/middleware.py` | Modificação cirúrgica |
| Novo loader de documento | `retrieval/loaders/` | Adição |
| Novo vector store | `retrieval/vector/dbs/` | Adição |
| Novo componente UI | `src/lib/components/` | Adição |
| Novo store de estado | `src/lib/stores/` | Adição |
| Variáveis de configuração | `config.py` + `env.py` | Adição |

---

## Como usar este processo em outros projetos

1. Clonar/forkar o projeto alvo
2. Criar `docs/reengenharia/README.md` com o mapa inicial (este template)
3. Seguir o roteiro de leitura e preencher os artefatos na ordem
4. Registrar **toda** decisão de customização em `customizacoes.md` e `decisoes.md`
5. Antes de cada sessão de trabalho: ler `customizacoes.md` para retomar contexto

---

## Status do mapeamento

- [x] Estrutura de arquivos
- [x] Entry point e routers (`main.py`)
- [x] Mapa de domínios (rascunho)
- [x] Fluxo de uma conversa end-to-end → [`fluxo-conversa.md`](fluxo-conversa.md)
- [x] Schema de dados detalhado → [`schema-dados.md`](schema-dados.md)
- [ ] Fluxo de autenticação e autorização
- [ ] Pipeline RAG detalhado
- [ ] Mapa de componentes Svelte
- [ ] Inventário de variáveis de configuração
