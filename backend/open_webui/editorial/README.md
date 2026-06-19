# Modulo Editorial (Nidum) — Fatias 1 e 2

Transforma o ChatND em assistente editorial.
- **Fatia 1:** camada de dados + endpoints de projeto e ficha (versionada).
- **Fatia 2:** ingestao real — recebe o `file_id` do upload nativo, le o arquivo
  (Files+Storage), extrai a **Arvore de Blocos** e guarda no Storage.
- **Fatia 3:** extratores `.pdf` (com **deteccao de escaneado** -> `needs_ocr`,
  sem fabricar texto), `.epub` e `.odt` (sem ebooklib/odfpy).
- **Fatia 4:** **chunking posicional** (chunks por capitulo, com `block_ids` e
  intervalo de caracteres para reconstrucao/citacao) + aceite do `.docx` de ~80k
  palavras (capitulos e notas sem perda). Export (F2) vem depois.

**Formatos suportados:** `.docx`, `.pdf`, `.epub`, `.odt`. Todos produzem a mesma
Arvore de Blocos. Notas de rodape ficam ligadas a ancora (`footnote_ref` <-> `footnote`)
em docx/epub/odt; no PDF, se nao houver camada de texto, sinaliza `needs_ocr`.

## Arquivos novos

| Arquivo | Papel |
|---|---|
| `models/editorial.py` | Tabelas `editorial_project`, `editorial_project_sheet` (ficha versionada), `editorial_document` + helper-classes `Projects`, `Sheets`, `Documents`. |
| `routers/editorial.py` | Endpoints REST (prefixo `/api/v1/editorial`). |
| `editorial/jobs.py` | Fila de jobs com modo **inline** (sem Redis). Backend `arq` entra na Fatia 2+. |
| `editorial/extractors/docx.py` | Extrator `.docx` -> Arvore de Blocos (puro: stdlib+lxml+python-docx). |
| `editorial/extractors/__init__.py` | Registro de extratores por formato + `detect_format`. |
| `editorial/ingest.py` | Ingestao: file_id -> Files/Storage -> extrator -> guarda arvore -> status. |
| `migrations/versions/b7e1c4a9d2f3_add_editorial_tables.py` | Migracao Alembic (cria as 3 tabelas + indices). |
| `test/editorial/test_editorial.py` | Testes de dados (SQLite em memoria, sem Redis). |
| `test/editorial/test_docx_extractor.py` | Testes do extrator (ancora<->nota, erro claro). |
| `test/editorial/test_ingest.py` | Teste de integracao da ingestao (Files/Storage mockados). |

## Endpoints

| Metodo | Rota | Descricao |
|---|---|---|
| POST | `/api/v1/editorial/projects` | Cria projeto (dono = autor logado). |
| GET | `/api/v1/editorial/projects` | Lista projetos do autor. |
| GET | `/api/v1/editorial/projects/{id}` | Detalhe (404 se nao for do autor). |
| GET | `/api/v1/editorial/projects/{id}/sheet` | Ficha **atual** (versao current). |
| POST | `/api/v1/editorial/projects/{id}/sheet` | Cria **nova versao** da ficha (preserva a anterior). |
| GET | `/api/v1/editorial/projects/{id}/sheet/versions` | Historico de versoes (desc). |
| POST | `/api/v1/editorial/projects/{id}/documents` | Registra `{file_id}` e **dispara a ingestao** (202). No modo inline ja volta `done`. |
| GET | `/api/v1/editorial/documents/{id}` | Status do documento (`pending/parsing/done/error` + `meta`). |
| GET | `/api/v1/editorial/documents/{id}/tree` | Arvore de Blocos extraida (409 se ainda indisponivel). |
| GET | `/api/v1/editorial/documents/{id}/chunks` | Chunks posicionais (409 se ainda indisponivel). |
| POST | `/api/v1/editorial/documents/{id}/export?format=docx\|epub\|pdf` | Exporta a obra (F2.1 `.docx`, F2.2 `.epub`, F2.3 `.pdf`). |

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
