# Schema de Dados

> Mapeado a partir de: `backend/open_webui/models/*.py` + `internal/db.py`  
> Data: 2026-05-06

---

## Visão geral

O banco de dados é relacional (SQLite em dev, PostgreSQL em prod) gerenciado via SQLAlchemy + Alembic. **Não há foreign keys declaradas no schema** — as relações são mantidas por convenção no código da aplicação, usando campos `*_id` do tipo String/Text.

Todos os timestamps são **Unix epoch em BigInteger** (segundos). Campos `meta`, `data`, `settings` e `access_control` são blobs JSON que estendem o schema sem migrations.

### Tabelas (16)

| Tabela | Domínio | Linhas esperadas |
|--------|---------|-----------------|
| `user` | Identidade | baixo (usuários da instância) |
| `auth` | Identidade | 1:1 com user |
| `chat` | Conversa | alto |
| `message` | Canal/Conversa | alto |
| `message_reaction` | Canal | médio |
| `channel` | Colaboração | médio |
| `tag` | Organização | médio |
| `folder` | Organização | médio |
| `file` | Conteúdo | médio-alto |
| `knowledge` | RAG | baixo-médio |
| `memory` | Memória pessoal | médio |
| `model` | Configuração | baixo |
| `prompt` | Customização | baixo |
| `tool` | Extensão | baixo |
| `function` | Extensão | baixo |
| `group` | Controle de acesso | baixo |
| `feedback` | Avaliação | médio |

---

## ERD simplificado

```
┌──────────┐      ┌──────────┐
│   auth   │      │  group   │
│ id (PK)  │      │ id (PK)  │
│ email    │      │ user_id  │──────────────────────┐
│ password │      │ user_ids │ (lista em JSON)       │
└────┬─────┘      └──────────┘                       │
     │ 1:1                                            │
┌────▼─────────────────────────────────┐             │
│                 user                  │◄────────────┘
│ id (PK) · name · email · role        │
│ api_key · settings(JSON) · info(JSON)│
│ oauth_sub · last_active_at           │
└────┬─────────────────────────────────┘
     │
     ├──────────────────┬─────────────────┬──────────────────┬──────────────────┐
     │                  │                 │                  │                  │
┌────▼─────┐    ┌───────▼──────┐  ┌──────▼─────┐   ┌───────▼──────┐   ┌───────▼──────┐
│   chat   │    │   channel    │  │    file    │   │   knowledge  │   │   memory     │
│ id (PK)  │    │ id (PK)      │  │ id (PK)    │   │ id (PK)      │   │ id (PK)      │
│ user_id  │    │ user_id      │  │ user_id    │   │ user_id      │   │ user_id      │
│ title    │    │ name · type  │  │ filename   │   │ name         │   │ content      │
│ chat(JSON│    │ access_ctrl  │  │ hash · path│   │ description  │   └──────────────┘
│ folder_id│    └──────┬───────┘  │ data(JSON) │   │ data(JSON)   │
│ share_id │           │          │ meta(JSON) │   │ access_ctrl  │
│ archived │    ┌──────▼───────┐  │ access_ctrl│   └──────────────┘
│ pinned   │    │   message    │  └────────────┘
│ meta(JSON│    │ id (PK)      │
└────┬─────┘    │ user_id      │
     │          │ channel_id   │
     │          │ parent_id ──┐│  (auto-ref: threads)
     │          │ content     ││
     │          │ data(JSON)  ││
     │          │ meta(JSON)  ◄┘
     │          └──────┬───────┘
     │                 │
     │          ┌──────▼───────────┐
     │          │ message_reaction  │
     │          │ id · user_id      │
     │          │ message_id · name │
     │          └───────────────────┘
     │
     ├─────────────────┬──────────────────┐
     │                 │                  │
┌────▼─────┐   ┌───────▼──────┐   ┌───────▼──────┐
│  folder  │   │     tag      │   │   feedback   │
│ id (PK)  │   │ id+user_id   │   │ id (PK)      │
│ parent_id│──▶│ (composite PK│   │ user_id      │
│ user_id  │   │ name · meta) │   │ type · data  │
│ name     │   └──────────────┘   │ meta(JSON)   │
│ items(JS)│                      │ snapshot(JSON│
│ meta(JS) │                      └──────────────┘
└──────────┘

┌──────────┐   ┌──────────┐   ┌──────────┐
│  model   │   │   tool   │   │ function │
│ id (PK)  │   │ id (PK)  │   │ id (PK)  │
│ user_id  │   │ user_id  │   │ user_id  │
│base_model│   │ name     │   │ name     │
│ name     │   │ content  │   │ type     │
│params(JS)│   │ specs(JS)│   │ content  │
│ meta(JS) │   │ meta(JS) │   │ meta(JS) │
│access_ctrl   │ valves(JS│   │ valves(JS│
│ is_active│   │access_ctrl   │is_active │
└──────────┘   └──────────┘   │is_global │
                               └──────────┘

┌──────────┐
│  prompt  │
│command(PK│
│ user_id  │
│ title    │
│ content  │
│access_ctrl
└──────────┘
```

---

## Tabelas — detalhamento

### `auth`
Separada de `user` para isolar credenciais. Relacionamento 1:1 por `id`.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | mesmo valor do `user.id` |
| `email` | String | — |
| `password` | Text | hash bcrypt |
| `active` | Boolean | conta ativa |

### `user`
Perfil e configurações do usuário.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | UUID |
| `name` | String | — |
| `email` | String | — |
| `role` | String | `"admin"` \| `"user"` \| `"pending"` |
| `profile_image_url` | Text | URL ou base64 |
| `api_key` | String | nullable, unique — para acesso via API |
| `oauth_sub` | Text | nullable, unique — subject do provider OAuth |
| `settings` | JSON | `UserSettings {ui: {}, ...}` — preferências da UI |
| `info` | JSON | dados extras livres |
| `last_active_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |
| `created_at` | BigInteger | epoch |

**Roles:** `pending` (aguarda aprovação) → `user` → `admin`

### `chat`
O registro central de uma conversa. O histórico completo vive em `chat` (JSON blob).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | UUID |
| `user_id` | String | ref lógica → `user.id` |
| `title` | Text | título exibido na sidebar |
| `chat` | JSON | **blob completo da conversa** — ver estrutura abaixo |
| `share_id` | Text | nullable, unique — ID público se compartilhado |
| `archived` | Boolean | default False |
| `pinned` | Boolean | default False |
| `folder_id` | Text | nullable — ref lógica → `folder.id` |
| `meta` | JSON | `{}` — metadados extras (ex: tags via `chat.meta.tags`) |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

**Estrutura do `chat.chat` (JSON blob):**
```json
{
  "title": "Nome do chat",
  "history": {
    "currentId": "<message_id>",
    "messages": {
      "<message_id>": {
        "id": "<uuid>",
        "parentId": "<uuid> | null",
        "childrenIds": ["<uuid>"],
        "role": "user | assistant",
        "content": "texto da mensagem",
        "model": "model_id",
        "timestamp": 1234567890,
        "done": true,
        "files": [...],
        "statusHistory": [...],
        "error": null
      }
    }
  },
  "models": ["model_id"],
  "tags": [],
  "params": {}
}
```

> O histórico é um **grafo** (não lista) — cada mensagem aponta para pai e filhos, suportando branches de conversa (regenerar resposta cria um novo nó filho).

### `message`
Mensagens de **canais** (colaboração em tempo real). Diferente das mensagens de chat, que ficam no blob `chat.chat`.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | — |
| `user_id` | Text | ref → `user.id` |
| `channel_id` | Text | nullable — ref → `channel.id` |
| `parent_id` | Text | nullable — auto-ref (threads/respostas) |
| `content` | Text | conteúdo da mensagem |
| `data` | JSON | dados extras (ex: anexos) |
| `meta` | JSON | metadados |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `message_reaction`
Reações emoji em mensagens de canal.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | — |
| `user_id` | Text | ref → `user.id` |
| `message_id` | Text | ref → `message.id` |
| `name` | Text | emoji ou nome da reação |
| `created_at` | BigInteger | epoch |

### `channel`
Canais de comunicação em tempo real (tipo Slack/Discord).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | — |
| `user_id` | Text | criador |
| `name` | Text | — |
| `type` | Text | nullable |
| `description` | Text | nullable |
| `data` | JSON | nullable |
| `meta` | JSON | nullable |
| `access_control` | JSON | nullable — ver padrão ACL abaixo |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `file`
Arquivos enviados (documentos, imagens, etc.).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | UUID |
| `user_id` | String | ref → `user.id` |
| `hash` | Text | nullable — hash do conteúdo (deduplicação) |
| `filename` | Text | nome original |
| `path` | Text | nullable — caminho no storage local ou S3 key |
| `data` | JSON | nullable — conteúdo processado (ex: texto extraído) |
| `meta` | JSON | nullable — `{name, content_type, size, ...}` |
| `access_control` | JSON | nullable |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `folder`
Hierarquia de pastas para organizar chats.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | — |
| `parent_id` | Text | nullable — **auto-referência** (hierarquia) |
| `user_id` | Text | ref → `user.id` |
| `name` | Text | — |
| `items` | JSON | nullable |
| `meta` | JSON | nullable |
| `is_expanded` | Boolean | estado de UI |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `knowledge`
Base de conhecimento para RAG. Cada registro representa uma coleção no vector store.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | mesmo valor usado como `collection_name` no vector DB |
| `user_id` | Text | criador |
| `name` | Text | — |
| `description` | Text | — |
| `data` | JSON | nullable — `{file_ids: [...]}` (arquivos indexados) |
| `meta` | JSON | nullable |
| `access_control` | JSON | nullable |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `memory`
Memórias pessoais do usuário (injetadas automaticamente no system prompt).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | UUID |
| `user_id` | String | ref → `user.id` |
| `content` | Text | texto da memória |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `model`
Modelos customizados (overrides de modelos Ollama/OpenAI ou modelos virtuais).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | ID usado nas chamadas à API |
| `user_id` | Text | criador |
| `base_model_id` | Text | nullable — ID do modelo real (Ollama/OpenAI) |
| `name` | Text | nome exibido |
| `params` | JSON | `ModelParams` — temperatura, top_p, etc. (`extra="allow"`) |
| `meta` | JSON | `ModelMeta {profile_image_url, description, capabilities, knowledge: [...]}` |
| `access_control` | JSON | nullable — ver padrão ACL |
| `is_active` | Boolean | default True |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

**Campo `meta.knowledge`:** lista de referências a `knowledge.id` ou `file.id` — define o RAG automático do modelo.

### `prompt`
Prompts reutilizáveis (slash commands tipo `/meu-prompt`).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `command` | String PK | ex: `/resumir` |
| `user_id` | String | criador |
| `title` | Text | — |
| `content` | Text | template do prompt (suporta variáveis) |
| `access_control` | JSON | nullable |
| `timestamp` | BigInteger | epoch |

### `tool`
Ferramentas Python executáveis pelo LLM (function calling).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | — |
| `user_id` | String | criador |
| `name` | Text | nome exibido |
| `content` | Text | **código Python da tool** |
| `specs` | JSON | especificações OpenAI function calling das funções |
| `meta` | JSON | `ToolMeta {description, manifest}` |
| `valves` | JSON | configurações da tool (parâmetros injetados em runtime) |
| `access_control` | JSON | nullable |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `function`
Funções Python que interceptam o pipeline de chat.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String PK | — |
| `user_id` | String | criador |
| `name` | Text | — |
| `type` | Text | `"filter"` \| `"action"` \| `"pipe"` |
| `content` | Text | **código Python da função** |
| `meta` | JSON | metadados |
| `valves` | JSON | configurações injetadas em runtime |
| `is_active` | Boolean | ativa/desativa no pipeline |
| `is_global` | Boolean | aplica a todos os modelos |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

**Tipos de função:**
- `filter` — intercepta inlet (pré) e outlet (pós) do pipeline de chat
- `action` — botões de ação na UI das mensagens
- `pipe` — novo modelo virtual (executa código Python no lugar do LLM)

### `group`
Grupos de usuários para controle de acesso.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | UUID |
| `user_id` | Text | criador/owner |
| `name` | Text | — |
| `description` | Text | — |
| `data` | JSON | nullable |
| `meta` | JSON | nullable |
| `permissions` | JSON | nullable — permissões do grupo |
| `user_ids` | JSON | lista de IDs dos membros |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `feedback`
Avaliações de respostas (thumbs up/down, arena).

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | Text PK | UUID |
| `user_id` | Text | avaliador |
| `version` | BigInteger | default 0 |
| `type` | Text | ex: `"rating"`, `"arena"` |
| `data` | JSON | `RatingData {rating, model_id, sibling_model_ids, reason, comment}` |
| `meta` | JSON | `MetaData {arena, chat_id, message_id, tags}` |
| `snapshot` | JSON | `SnapshotData {chat}` — snapshot do chat no momento do feedback |
| `created_at` | BigInteger | epoch |
| `updated_at` | BigInteger | epoch |

### `tag`
Tags para organização de chats.

| Coluna | Tipo | Obs |
|--------|------|-----|
| `id` | String | parte da chave composta |
| `user_id` | String | parte da chave composta — tags são por usuário |
| `name` | String | nome exibido |
| `meta` | JSON | nullable |

> Tags são referenciadas em `chat.meta.tags` (lista de strings) — não há tabela de junção explícita.

---

## Padrão de controle de acesso (`access_control`)

Reutilizado em `model`, `knowledge`, `tool`, `prompt`, `channel`, `file`:

```json
null        → público (qualquer usuário com role "user")
{}          → privado (somente o owner)
{
  "read": {
    "group_ids": ["gid1"],
    "user_ids":  ["uid1"]
  },
  "write": {
    "group_ids": ["gid1"],
    "user_ids":  ["uid1"]
  }
}
```

A verificação é feita por `utils/access_control.py → has_access(user_id, permission, access_control)`.

---

## Duas arquiteturas de mensagem em paralelo

| | Chat (IA) | Channel (colaboração) |
|---|---|---|
| Tabela | `chat.chat` (JSON blob) | `message` (tabela própria) |
| Estrutura | Grafo de nós (suporta branches) | Lista com parent_id (threads) |
| Persistência | Batch (save ao fim do stream) | Tempo real (via WebSocket) |
| Busca | `Chats.get_messages_by_chat_id()` | `Messages` table query |
| Reações | Não há | `message_reaction` |

---

## Campos JSON de alto risco em customizações

Estes campos não têm schema fixo e crescem por convenção — mudanças podem quebrar silenciosamente:

| Campo | Tabela | O que guardar com cuidado |
|-------|--------|--------------------------|
| `chat.chat` | `chat` | estrutura do grafo de mensagens |
| `meta.knowledge` | `model` | lista de fontes RAG do modelo |
| `settings.ui` | `user` | preferências de UI do usuário |
| `data.file_ids` | `knowledge` | arquivos indexados na coleção |
| `specs` | `tool` | contrato das funções para o LLM |
| `valves` | `tool` / `function` | configurações runtime — sem validação automática |

---

## Migrations

Gerenciadas via Alembic em `backend/open_webui/internal/migrations/`. Ao adicionar colunas em customizações, sempre criar migration — nunca alterar o schema diretamente.
