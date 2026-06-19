# Modulo Editorial (Nidum) — Fatia 1

Transforma o ChatND em assistente editorial. Esta fatia entrega a **camada de
dados** e os **endpoints de projeto e ficha**. A ingestao/parse de obras e o
export entram nas fatias seguintes.

## Arquivos novos

| Arquivo | Papel |
|---|---|
| `models/editorial.py` | Tabelas `editorial_project`, `editorial_project_sheet` (ficha versionada), `editorial_document` + helper-classes `Projects`, `Sheets`, `Documents`. |
| `routers/editorial.py` | Endpoints REST (prefixo `/api/v1/editorial`). |
| `editorial/jobs.py` | Fila de jobs com modo **inline** (sem Redis). Backend `arq` entra na Fatia 2. |
| `migrations/versions/b7e1c4a9d2f3_add_editorial_tables.py` | Migracao Alembic (cria as 3 tabelas + indices). |
| `test/editorial/test_editorial.py` | Testes (SQLite em memoria, sem Redis). |

## Endpoints

| Metodo | Rota | Descricao |
|---|---|---|
| POST | `/api/v1/editorial/projects` | Cria projeto (dono = autor logado). |
| GET | `/api/v1/editorial/projects` | Lista projetos do autor. |
| GET | `/api/v1/editorial/projects/{id}` | Detalhe (404 se nao for do autor). |
| GET | `/api/v1/editorial/projects/{id}/sheet` | Ficha **atual** (versao current). |
| POST | `/api/v1/editorial/projects/{id}/sheet` | Cria **nova versao** da ficha (preserva a anterior). |
| GET | `/api/v1/editorial/projects/{id}/sheet/versions` | Historico de versoes (desc). |
| POST | `/api/v1/editorial/projects/{id}/documents` | Registra documento p/ ingestao (202; parse na Fatia 2/3). |
| GET | `/api/v1/editorial/documents/{id}` | Status do documento. |

**Isolamento:** toda rota exige posse do projeto pelo autor (`user_id`); admin
acessa para suporte. Um autor nunca acessa projeto/ficha de outro.

## Ficha viva — formato do campo `data` (JSON)

```jsonc
{
  "tone_of_voice": "texto livre",
  "glossary":       [ { "term": "...", "definition": "...", "do": "...", "dont": "..." } ],
  "characters":     [ { "name": "...", "aliases": ["..."], "description": "...", "notes": "..." } ],
  "style_decisions":[ { "topic": "...", "decision": "...", "rationale": "..." } ],
  "terminology":    [ { "preferred": "...", "avoid": ["..."], "context": "..." } ],
  "free_notes": "markdown livre"
}
```

Estruturado de proposito para a UI dedicada futura (cada lista vira form/tabela).

## Versionamento da ficha

Cada alteracao **insere uma linha nova** (`version = max+1`, `is_current=True`) e
**rebaixa** a anterior, na mesma transacao. Nunca apaga. Um **indice unico
parcial** (`uq_sheet_one_current_per_project`, `WHERE is_current`) garante **no
banco** no maximo uma current por projeto (funciona em SQLite e PostgreSQL).

## Fila de jobs

`EDITORIAL_JOB_BACKEND` = `inline` (default) | `arq`. Em `inline` nada externo e
necessario (Fatia 1). O import de `arq`/`redis` so ocorre se `arq` for escolhido.

## Bibliotecas e licencas (uso comercial)

Verificadas no PyPI em 2026-06-19. Extratores (F1): **python-docx** (MIT),
**pdfplumber** (MIT), **pdfminer.six** (MIT), **pypdf** (BSD, ja no projeto);
`.epub`/`.odt` via `zipfile` (stdlib) + **lxml** (BSD-3). **Banidas por AGPL:**
PyMuPDF e ebooklib. Fila: **arq** (MIT) + **redis** client (MIT) na Fatia 2.

## Testes

```bash
cd backend
pip install -r requirements.txt -r requirements-test.txt
pytest
```

Os testes usam SQLite em memoria e o modo inline — **nao precisam de Redis**.
```

> O criterio de aceite do `.docx` (Fatia 3) e VINCULANTE: a ancora da nota no
> corpo deve continuar resolvendo para o texto da nota (footnote_ref.id == footnote.id),
> nao basta a nota existir.
