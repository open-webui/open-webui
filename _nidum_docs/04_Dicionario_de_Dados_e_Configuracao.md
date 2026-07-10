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
| `STORAGE_PROVIDER` | Onde os arquivos são salvos | local (volume); `s3` no futuro |
| `NIDUM_API_KEY` | Chave de API do **próprio Open WebUI** (admin), usada para publicar roteador/ferramenta | `.env.local` (local, gitignored) |

> O `OPENAI_API_KEY` no `.env.local` local pode estar desatualizado; o valor que vale para o **app** é o salvo dentro do Open WebUI (Configurações → Conexões/Documentos). O Open WebUI guarda algumas chaves **no banco** após o boot.

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
