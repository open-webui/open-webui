# 04 — Dicionário de Dados e Configuração

> **Para quem é:** quem configura, debuga ou precisa saber o significado exato de uma variável, valve, id ou tabela.
> **Quando consultar:** ao ajustar configuração, ler logs, ou entender um identificador.

> ⚠️ Valores reais de chaves **não** aparecem aqui — só os **nomes** e o significado. Os valores vivem no Bitwarden e nas variáveis do Railway / `.env.local`.

---

## Variáveis de ambiente (Railway / `.env`)

| Variável | Significado | Valor típico |
|---|---|---|
| `OPENAI_API_KEY` | Chave da OpenAI (chat + embeddings) | (secreta) |
| `ANTHROPIC_API_KEY` | Chave da Anthropic (Claude) | (secreta) |
| `IMAGES_GEMINI_API_KEY` / `GEMINI_API_KEY` | Chave do Google (geração de imagem) | (secreta) |
| `WEBUI_SECRET_KEY` | Criptografa sessões; se mudar, todos deslogam | string 64 chars |
| `WEBUI_NAME` | Nome exibido na interface | `Nidum AI` |
| `ENABLE_SIGNUP` | Permite cadastro (com aprovação) | `true` |
| `DEFAULT_USER_ROLE` | Papel inicial de novo usuário | `pending` |
| `UVICORN_WORKERS` | Processos do servidor (manter enxuto) | `1` |
| `RAG_EMBEDDING_ENGINE` | Motor de embeddings | `openai` |
| `ENABLE_RAG_HYBRID_SEARCH` | Busca híbrida BM25 + vetorial | `True` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Tamanho/sobreposição dos trechos | `2200` / `300` |
| `ENABLE_CODE_INTERPRETER` | Interpretador de código no navegador | `False` (desligado de propósito) |
| `ENABLE_IMAGE_GENERATION` | Geração de imagem nativa | `True` |
| `ENABLE_DB_MIGRATIONS` | Roda migrações Alembic no boot | `True` |
| `STORAGE_PROVIDER` | Onde os arquivos são salvos. **`s3` não é "em vez do disco" — é "disco E R2"**: o provedor grava local **e** sobe. O disco é cópia permanente de tudo que passa | **`s3`** |
| **`ENABLE_WEB_SEARCH`** | **`False` — de propósito, mesmo com o ChatND buscando na web.** Leia o quadro abaixo **antes** de mexer | **`False`** |
| `WEB_SEARCH_ENGINE` | Buscador da rota `geral` | `duckduckgo` |
| `NIDUM_API_KEY` | Chave de API do **próprio Open WebUI** (admin), usada para publicar roteador/ferramenta | `.env.local` (local, gitignored) |

> O `OPENAI_API_KEY` no `.env.local` local pode estar desatualizado; o valor que vale para o **app** é o salvo dentro do Open WebUI (Configurações → Conexões/Documentos). O Open WebUI guarda algumas chaves **no banco** após o boot.

### 🚨 `ENABLE_WEB_SEARCH=False` **enquanto o ChatND busca na web** — isto NÃO é bug

> **Se você chegou aqui achando que achou uma inconsistência: não achou. É desenho, e ligar essa variável quebra uma garantia.**

**A regra em uma frase:** *só o pipe aciona a web, e só na rota `geral`. As rotas institucionais nunca veem conteúdo da internet.*

**Por que a variável fica `False`.** O Open WebUI tem um caminho **próprio** de web search, que roda **antes** do pipe (`utils/middleware.py`, dentro do `process_chat_payload`). Esse caminho é **cego ao contexto**: se ligado, ele busca na internet em **toda** pergunta — inclusive *"qual o propósito da Nidum?"* — e injeta o resultado nas mensagens **antes** de o ChatND rodar. **O pipe não tem como impedir: quando ele acorda, a contaminação já aconteceu.**

**Defesa em duas camadas — as duas precisam ficar como estão:**

| Camada | Estado | O que impede |
|---|---|---|
| Permissão do grupo *"Pesquisa na Web"* | **OFF** | O **botão** não aparece; o usuário não liga o caminho pré-pipe |
| `ENABLE_WEB_SEARCH` | **`False`** | O **middleware** e o **endpoint** `/process/web/search` recusam (403) |

**E como o ChatND busca, então?** Ele chama a camada de baixo — **`search_web()`** (`routers/retrieval.py`) — que **não** olha essa variável nem a permissão. Ele chama **depois** de classificar, e **só** quando a rota é `geral`.

**Por que pular esses gates não é burlar segurança.** A permissão `features.web_search` significa *"o usuário pode ligar o toggle"*. **O pipe não é o usuário — é o sistema decidindo.** São coisas diferentes: *"o coautor pediu busca"* versus *"o ChatND concluiu que a pergunta não é da Nidum e foi buscar"*.

> ⚠️ **O que quebra se alguém ligar `ENABLE_WEB_SEARCH=True`:** volta o caminho pré-pipe. Basta um usuário com permissão clicar no botão para **uma pergunta institucional ser respondida com conteúdo da internet** — sobre uma empresa **homônima**, com confiança e citação. É o **erro silencioso**: ninguém percebe, porque a resposta *parece* fundamentada.

**Se um dia for preciso ligar:** a defesa passa a depender **só** da permissão do grupo — e aí a `ENABLE_WEB_SEARCH` deixa de ser camada e vira decoração. Não é impossível; é uma decisão de governança, e precisa ser tomada de propósito, não por engano ao "arrumar uma config estranha".

### Buscador (engine): **`duckduckgo`**

**Escolhido por não exigir nada:** sem chave, sem cadastro, sem custo. **Decisão registrada:** não faz sentido escolher um buscador pago antes de saber se o gratuito resolve perguntas factuais de volume baixo. **Trocar é mudar uma variável** — o código da rota `geral` não muda.

O fork suporta **28 engines**. Os que **não exigem chave**:

| Engine | Config |
|---|---|
| **`duckduckgo`** | nada (opcional: `DDGS_BACKEND`) |
| `ollama_cloud` | nada obrigatório |

Self-hosted (URL, não chave): `searxng` (`SEARXNG_QUERY_URL`), `yacy` (`YACY_QUERY_URL` + usuário/senha).

**Todos os demais exigem chave** — inclusive os que "parecem" nativos: `bing` (`BING_SEARCH_V7_SUBSCRIPTION_KEY` + `ENDPOINT`), `azure`, `jina`, `yandex`, `firecrawl`, `youcom`, `perplexity`, `sougou`, `external`, `google_pse` (chave **+** `ENGINE_ID`), `brave`, `tavily`, `exa`, `serper`, `serpapi`, `searchapi`, `serpstack`, `serply`, `kagi`, `mojeek`, `bocha`, `linkup`.

> **Como esta lista foi levantada — e por que a primeira versão estava errada.** Ela saiu do `search_web()` em `routers/retrieval.py`. Meu primeiro script marcou **9 engines como "sem chave"** — `bing`, `azure`, `jina`, `yandex`, `firecrawl`, `external`, `youcom`, `perplexity`, `sougou`. **Todos exigem chave.** O regex não pegava o formato da condição deles. **Se a lista errada tivesse sido usada, alguém escolheria o Bing achando que era grátis.** Ao reconferir um engine aqui, **leia o bloco `elif engine == '<nome>'` no código** — não confie em busca por padrão.

## Valves do roteador ChatND

Configuráveis ao vivo via `POST /api/v1/functions/id/chatnd/valves/update`.

| Valve | Significado | Default no código | Valor em produção |
|---|---|---|---|
| `ROUTER_MODEL` | Modelo do classificador | `gpt-5-mini` | idem |
| `GERADOR_MODEL` | Modelo que monta a estrutura de arquivos | `gpt-5.1` | idem |
| `TOOL_ID` | Id da ferramenta de arquivos | `gerador_de_arquivos_nidum` | idem |
| `MODELO_RAPIDO` | Motor da rota rápido | `nidum-10---rpido` | idem |
| `MODELO_DIADIA` | Motor da rota dia a dia | `nidum-10---dia-a-dia` | idem |
| `MODELO_DOCUMENTOS` | Motor da rota documentos | `nidum-10---documentos` | idem |
| `MODELO_RACIOCINIO` | Motor da rota raciocínio | `nidum-20---raciocinio` | idem |
| `BASE_CONHECIMENTO_ID` | Base de conhecimento (RAG) | `f2c8a48c...` ⚠️ (base morta) | **`a85d8a8f...`** (via valve) |
| `TOP_K_DOCUMENTOS` | Quantos trechos buscar p/ rankear | `10` | idem |
| `MAX_DOCS_INTEIROS` | Quantos documentos inteiros injetar | `2` | idem |
| `MAX_CHARS_TOTAL` | Teto de caracteres injetados | `200000` | idem |
| `MOSTRAR_ROTA` | Mostra "ChatND encaminhou para..." | `False` | idem |
| `TRIADE_ATIVA` | Liga/desliga a voz da tríade | `True` | idem |

> ⚠️ O default de `BASE_CONHECIMENTO_ID` no código aponta para uma base **morta**; só funciona porque a valve em produção sobrescreve para `a85d8a8f`. **Alinhar o default é um pendente** (ver [08_Decisoes_e_Pendencias](08_Decisoes_e_Pendencias.md)).

## Identificadores fixos (produção)

| O quê | Id / valor |
|---|---|
| Org GitHub | `nidum-oficial-tec` |
| Repositório | `nidum-platform` (fork de `open-webui/open-webui`) |
| Projeto Railway | `surprising-flow` · serviço `nidum-platform` · região `sfo` |
| Volume | `/app/backend/data` (500 MB) |
| Domínio | `chatnd.nidumbrasil.com.br` |
| Função roteadora | `chatnd` (nome "ChatND") |
| Ferramenta de arquivos | `gerador_de_arquivos_nidum` |
| Base de conhecimento ativa | `a85d8a8f-86de-4f9a-8393-08325abe384a` ("MVP - Agente Chico") |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vetores | ChromaDB (coleção por base; `file-{id}` por arquivo) |

## Controle de acesso (modelos)

- **Wrappers (motores):** `access_grants = []` → **privados** (só o dono os vê).
- **ChatND:** grant `{principal_type:user, principal_id:"*", permission:read}` → **público** (todo usuário vê só a ChatND).
- **Cadastro:** `DEFAULT_USER_ROLE=pending`; o admin aprova cada novo usuário em Painel de Admin → Usuários, e **só deve aprovar e-mails `@nidumbrasil.com.br`** (a checagem de domínio é manual).

## Convenção de nomenclatura

| Padrão | Significado |
|---|---|
| `_nidum_*/` (pastas na raiz) | Código/conteúdo específico da Nidum (não-upstream): `_nidum_docs`, `_nidum_tools`, `_nidum_manutencao` |
| `nidum-10---*` | Wrappers "NIDUM 1.0" |
| `nidum-20---*` | Wrapper "NIDUM 2.0" (raciocínio; o slug manteve o "2.0") |
| `MKT_*` (arquivos da base) | Identidade visual (brandbook/template) — **não** vira conteúdo de respostas |
| `Fonte/Documentos` (subpasta da base) | Documentos fundadores (v29/v30 etc.) |

## Modelo de dados da Editorial (tabelas)

Criadas por migração Alembic (`backend/open_webui/migrations/versions/...add_editorial_tables.py`). Visão de alto nível:

| Tabela | Guarda |
|---|---|
| Projetos editoriais | Projeto por autor (isolado por `user_id`) |
| Fichas (sheets) | "Ficha viva" do projeto, **versionada** (uma só `is_current` por projeto, garantido por índice único parcial) |
| Documentos | Obras ingeridas: status (`pending/parsing/done/error`) + referências para a Árvore de Blocos e chunks no Storage |

> A "Árvore de Blocos Nidum" (JSON com lista plana e ordenada de blocos + chunks com referência posicional) é o formato intermediário da ingestão. Detalhes: `backend/open_webui/editorial/README.md`.
