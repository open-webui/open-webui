# 03 — Arquitetura e Motor

> **Para quem é:** quem precisa entender como o sistema pensa por dentro — para alterar o comportamento, debugar ou avaliar uma proposta técnica.
> **Quando consultar:** antes de mexer no roteador, nos motores, no RAG ou na geração de arquivos.

---

## Camadas do sistema

```
            Usuário (navegador, chatnd.nidumbrasil.com.br)
                                │
                  Open WebUI (FastAPI + SvelteKit)        ← software-base (fork)
                                │
                      Função Pipe "ChatND"                ← o MOTOR (código Nidum)
                                │  classifica e encaminha
          ┌──────────┬─────────┼──────────┬───────────┬──────────┐
        rápido    dia a dia  documentos  raciocínio  arquivo    imagem
        (motores wrapper = base model + system prompt)   │          │
                                │                   ferramenta   Gemini
                          RAG (ChromaDB)            de arquivos  (oculto)
                          base a85d8a8f
```

- **Open WebUI (o fork):** dá login, usuários, upload de arquivos, armazenamento (Storage), base de conhecimento e a infraestrutura de chat. É o "chassi".
- **ChatND (o motor):** uma **Função Pipe** (id `chatnd`) que se comporta como um "modelo" no seletor, mas na verdade **classifica e redireciona**. É **aditiva** — não altera os motores, só os orquestra.
- **Motores wrapper:** modelos customizados (`base model` + `system prompt` + regras), invisíveis ao usuário comum (privados); só a ChatND aparece para ele.

## O fluxo de uma mensagem (passo a passo)

1. O usuário manda uma mensagem para o "modelo" **ChatND**.
2. O ChatND chama um **classificador** (`gpt-5-mini`, prompt `CLASSIFICADOR`) que lê as últimas ~6 mensagens e devolve **uma** categoria: `imagem`, `arquivo`, `documentos`, `raciocinio`, `rapido` ou `diaadia`.
3. Conforme a categoria, o ChatND:
   - **imagem** → gera a imagem via Gemini (motor oculto) e devolve com legenda.
   - **arquivo** → busca contexto na base (RAG) + monta a estrutura do arquivo com `gpt-5.1` (`GERADOR`) + chama a **ferramenta de arquivos** → devolve um link de download.
   - **documentos** → faz **RAG modo documento-inteiro** e injeta o conteúdo antes de encaminhar ao motor *Documentos*.
   - **raciocinio / rapido / diaadia** → encaminha direto ao motor correspondente.
4. Em **documentos** e **raciocínio**, se o pedido for "gerativo" (movimento/relação/transformação), injeta-se a **voz da tríade** fonte/forma/fluxo (ver [09_Dominio_Nidum](09_Dominio_Nidum.md)).
5. O motor de destino responde; a resposta volta ao usuário.

> Código-fonte do motor: `_nidum_tools/chatnd_router.py` (versão atual **1.10.0**). Publicado **ao vivo** via API, **não** está versionado no git como deploy.

## Os motores (rotas) e quando cada um entra

| Rota | Motor / id | Base model (configurável por valve) | Para quê |
|---|---|---|---|
| `rapido` | `nidum-10---rpido` | modelo "mini" rápido (`gpt-5-mini`) | Saudações, perguntas triviais, traduções curtas |
| `diaadia` | `nidum-10---dia-a-dia` | modelo padrão (`gpt-5.1`) | Conversa geral, redação, análise comum |
| `documentos` | `nidum-10---documentos` | contexto longo (Claude Sonnet) | Perguntas sobre os documentos/livros da Nidum, com citação |
| `raciocinio` | `nidum-20---raciocinio` | modelo top (Claude Opus) | Decisões complexas, raciocínio profundo |
| `arquivo` | — (usa `GERADOR` + ferramenta) | `gpt-5.1` monta a estrutura | Gerar PPTX/PDF/DOCX/XLSX/HTML/deck |
| `imagem` | — (Gemini oculto) | `imagen-4.0-generate-001` | Gerar imagens |

> Os ids e base models são definidos por **valves** do roteador e podem mudar — confirmar sempre com `GET /api/models`. (Ver [04_Dicionario_de_Dados_e_Configuracao](04_Dicionario_de_Dados_e_Configuracao.md).)

## RAG — como o ChatND responde "pela Fonte"

O desafio: perguntas do tipo "liste todos os ecossistemas" precisam de informação **espalhada** pelo documento; busca por trechos (vetorial) trazia respostas fragmentadas e inconsistentes.

**Solução adotada (modo documento-inteiro):**
1. Recupera trechos **só para rankear** qual documento é o mais relevante (`_buscar_sources`, base `a85d8a8f`).
2. Injeta o(s) documento(s) **inteiro(s)** mais relevante(s) no contexto (`Knowledges.get_files_by_id` → conteúdo completo), limitado por `MAX_DOCS_INTEIROS=2` e `MAX_CHARS_TOTAL=200000`.
3. Se o pedido cita os **documentos fundadores** (v30/v29, Intenção Reta, "está Nidum", alinhamento, filosofia), a função `_docs_prioritarios` **força** esses documentos para o início da injeção — porque eles ficam em uma **subpasta** (`Fonte/Documentos`) e o ranking por vetores às vezes não os trazia ao topo.

**Por que assim:** completude e consistência acima de economia. O custo (~US$0,12/pergunta no motor de documentos, doc fundador ~40k tokens) foi aceito. Um *reranker* melhoraria precisão, mas **não** resolve completude — fica reservado para quando o corpus crescer.

> A base ativa é a **`a85d8a8f`** ("MVP - Agente Chico"). A base antiga `f2c8a48c` ficou órfã; o valor é sobrescrito por **valve** (`BASE_CONHECIMENTO_ID`). O default do código ainda aponta para a base antiga — corrigir esse default é um pendente (ver [08_Decisoes_e_Pendencias](08_Decisoes_e_Pendencias.md)).

## Geração de arquivos (rota `arquivo`)

- O `GERADOR` (`gpt-5.1`) **escreve um JSON** com a estrutura (`tipo`, `titulo`, `slides`/`secoes`/...) que o roteador parseia e repassa à **ferramenta** `gerador_de_arquivos_nidum` (versão **2.1.0**).
- A ferramenta produz o arquivo final **com a identidade da marca aplicada pelo código** (paleta, fontes Maxima Nouva + Ibrand, logos), salva via módulos internos do Open WebUI (`Storage` + `Files`) e devolve um link `/api/v1/files/{id}/content`.
- **Decisão-chave:** o **layout é decidido pelo código da ferramenta**, não por prompt nem RAG. Editar prompt/base **não** estiliza o arquivo.
- **Robustez (v1.8.0–1.9.0 do roteador):** se o JSON do GERADOR falhar ou vier vazio, há um *retry* único e uma mensagem amigável; `_parse_json` tolera prosa e cercas de código. Para pedidos com vários módulos, o roteador sugere gerar um por vez.

## Geração de imagens (rota `imagem`)

- Motor **oculto**: o pedido é refinado em uma descrição visual (`gpt-5-mini`, `IMAGEM_PROMPT`, já com a estética da marca) e enviado ao **Gemini** (`imagen-4.0-generate-001`, método `predict`).
- Chama a função **interna** `image_generations(...)` do Open WebUI (não o endpoint público), retornando a imagem inline. Saída em **PNG**.

## Frente Editorial (backend no fork)

Roda no mesmo servidor, por **API** (`/api/v1/editorial`), sem tela própria nesta rodada. Componentes:

| Componente | Arquivo | Função |
|---|---|---|
| Modelos de dados | `backend/open_webui/models/editorial.py` | 3 tabelas: projetos, fichas (versionadas), documentos |
| Rotas | `backend/open_webui/routers/editorial.py` | Ingestão, árvore, chunks, export, contexto |
| Extratores | `backend/open_webui/editorial/extractors/` | `.docx/.pdf/.epub/.odt` → "Árvore de Blocos Nidum" (JSON) |
| Export | `backend/open_webui/editorial/export/` | `.docx/.epub/.pdf` paginado + manual de estilo Nidum |
| Ficha (F3) | `editorial/project_context.py` | Ficha viva por autor injetada como contexto |

**Decisões de arquitetura:** estender o fork (não usar Tool/Function), interface API+chat (headless) nesta rodada, e Storage S3-compatível quando escalar (livros estouram o volume de 500 MB). Detalhes e formato intermediário: ver memória do projeto e `backend/open_webui/editorial/README.md`.

## Segurança (guardrails)

- **Nunca revelar** qual IA/modelo/provedor está por trás (regra inviolável nos motores).
- **Anti-injeção de prompt (LLM01):** o conteúdo recuperado é tratado como **dados, não instruções**; comandos embutidos são ignorados. É **mitigação, não garantia** — um modelo guard de input/output é recomendado antes de abrir uploads externos.
