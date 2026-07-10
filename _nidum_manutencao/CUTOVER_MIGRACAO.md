# Runbook — Cutover de armazenamento (Postgres + pgvector + R2)

> Migração A1 (fresh start): tirar o estado do volume SQLite/Chroma para **Postgres+pgvector**,
> e os arquivos para o bucket **Cloudflare R2**. Plataforma ainda em teste; downtime aceitavel.
> **NADA e apagado ate a nova camada estar validada** (volume/SQLite/Chroma antigos ficam de backup).

## Status (2026-07-02)
- [x] Postgres + pgvector no Railway (projeto ChatND / surprising-flow). pgvector 0.8.3 confirmado.
- [x] Bucket R2 `nidum-arquivos` + token (Object R/W, so nesse bucket). VALIDADO (put/get/list/delete).
      Endpoint: `https://f8f1cd274b3c01aa4b9809fc7eb54f29.r2.cloudflarestorage.com`
      Chaves R2 no `.env.local` (R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY) + Bitwarden.
- [x] Backup pre-migracao em `OneDrive\...\ChatND\backup_pre_migracao_2026-07-02_0900\`:
      - `fonte_arquivos/` = 28 arquivos da base do ChatND (9.6 MB) + `_manifesto.json`
      - `config_export.json` = 5 modelos, conexoes (mascaradas), estrutura da base
      - `funcoes_e_ferramentas/` = conteudo de: funcao chatnd, funcao roteador_semantico_da_fonte_nidum,
        tool gerador_de_arquivos_nidum, tool nidum_fonte_quadro_de_pessoas (+ valves)
- [ ] CUTOVER (agendado; fazer em horario de baixo uso).

## Variaveis a setar no servico `nidum-platform` (Railway)
| Variavel | Valor | Quem | Segredo? |
|---|---|---|---|
| `DATABASE_URL` | referencia `${{Postgres.DATABASE_URL}}` | usuario (painel) | interna |
| `VECTOR_DB` | `pgvector` | CLI | nao |
| `STORAGE_PROVIDER` | `s3` | CLI | nao |
| `S3_ENDPOINT_URL` | `https://f8f1cd274b3c01aa4b9809fc7eb54f29.r2.cloudflarestorage.com` | CLI | nao |
| `S3_BUCKET_NAME` | `nidum-arquivos` | CLI | nao |
| `S3_REGION_NAME` | `auto` | CLI | nao |
| `S3_ACCESS_KEY_ID` | (do .env.local R2_ACCESS_KEY_ID) | CLI ou painel | SIM |
| `S3_SECRET_ACCESS_KEY` | (do .env.local R2_SECRET_ACCESS_KEY) | CLI ou painel | SIM |

> `PGVECTOR_DB_URL` nao precisa: por padrao usa `DATABASE_URL`.
> As nao-secretas dao para setar via `railway variables --set "K=V"` (servico nidum-platform, env production).

## Passo a passo
1. [x] Backup Fonte + config + funcoes/tools (feito).
2. [ ] Setar as variaveis acima. Depois disso o Railway reconstroi e o Open WebUI sobe contra o Postgres VAZIO.
3. [ ] App sobe: Alembic cria o schema limpo. Plataforma fica EM BRANCO (sem usuarios/config).
4. [ ] Usuario: acessar chatnd.nidumbrasil.com.br -> criar a conta ADMIN (1o cadastro vira admin) ->
       Configuracoes -> Conta -> API Keys -> gerar -> colar no `.env.local` como `NIDUM_API_KEY`.
5. [ ] Conexoes: recriar OpenAI (api.openai.com/v1) e Anthropic (api.anthropic.com/v1); usuario cola as chaves.
6. [ ] RECRIAR CONFIG (via API, a partir dos backups):
       - Embedding: chave OpenAI em Configuracoes->Documentos (text-embedding-3-small).
       - RAG: ENABLE_RAG_HYBRID_SEARCH=True, CHUNK_SIZE=2200, CHUNK_OVERLAP=300.
       - Code Interpreter OFF (ENABLE_CODE_INTERPRETER=False).
       - Imagem: engine gemini, imagen-4.0-generate-001, predict, IMAGES_GEMINI_API_KEY, ENABLE_IMAGE_GENERATION=True.
       - Signup: ENABLE_SIGNUP=true, DEFAULT_USER_ROLE=pending. Follow-up: max 2.
       - 4 wrappers (nidum-10---rpido/dia-a-dia/documentos, nidum-20---raciocinio) com base_model_id + params.system
         (de config_export.json / funcoes_e_ferramentas) + access_grants=[] (privados).
       - Publicar funcoes: chatnd (v1.11.2) + roteador_semantico_da_fonte_nidum; ChatND grant "*" read (publica).
       - Publicar tools: gerador_de_arquivos_nidum (v2.1.0), nidum_fonte_quadro_de_pessoas.
       - Bloco SEGURANCA + "nao revelar LLM" + geracao de imagem nos system prompts dos wrappers.
7. [ ] Base de conhecimento: criar base NOVA (dono = admin, nao mais orfa) -> subir os 28 arquivos de
       `fonte_arquivos/` (vao para o R2 automaticamente) -> reindex/embed no pgvector. Recriar subpasta
       Fonte/Documentos (v29/v30). Setar valve BASE_CONHECIMENTO_ID do chatnd para o ID da base nova
       (corrigir tambem o DEFAULT no codigo, que aponta p/ f2c8a48c morto).
8. [ ] VALIDAR (roteiro do doc 06): olá; "empresa viva"; ecossistemas; gerar PPTX; imagem; nao revela LLM.
9. [ ] So apos validar: parar de depender do volume antigo (mantê-lo alguns dias como backup).
10.[ ] Atualizar `07_Diario_e_Status.md` e `08_Decisoes_e_Pendencias.md`.

## Retencao (fase seguinte, apos cutover)
- Comprimir (gzip) o conteudo de conversas inativas ha 5 dias.
- Deletar conversas com 90+ dias sem uso.
- Implementar como job no backend (nao ha nativo). Dry-run primeiro.

## Rollback
Reverter as variaveis (`DATABASE_URL`/`STORAGE_PROVIDER`/`VECTOR_DB` para os valores antigos / remover) ->
Railway reconstroi -> volta a usar o volume SQLite+Chroma+arquivos, que seguem intactos.
