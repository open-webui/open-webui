# 08 — Decisões e Pendências

> **Para quem é:** quem retoma o projeto ou precisa decidir algo, e quer saber o que já foi decidido (e por quê) e o que ainda está em aberto.
> **Quando consultar:** antes de propor uma mudança de rumo ou reabrir uma discussão.

---

## Parte 1 — Decisões já tomadas (e o porquê)

| # | Decisão | Por quê |
|---|---|---|
| D1 | **Estender o fork do Open WebUI** (não criar do zero) | Reaproveita login, usuários, Storage, RAG, UI. Custo aceito: fork mais pesado de manter. |
| D2 | **Roteamento por um "motor invisível" (ChatND)** em vez de o usuário escolher o modelo | Simplicidade para o usuário; ele só vê uma IA, a da Nidum. |
| D3 | **RAG modo documento-inteiro** (não só trechos) | Trechos davam respostas fragmentadas/incompletas. Doc inteiro garante completude. Custo (~US$0,12/pergunta) aceito. |
| D4 | **Layout dos arquivos no código da ferramenta**, não em prompt | Garante identidade da marca consistente; prompt/RAG não estilizam arquivo. |
| D5 | **Wrappers privados + só a ChatND pública** | Usuário comum vê só a ChatND; motores ficam ocultos. |
| D6 | **Controle de acesso por aprovação manual** (não OAuth) | `nidumbrasil.com.br` não é Google Workspace; e-mails não são contas Google. Admin aprova só `@nidumbrasil.com.br`. |
| D7 | **Nunca revelar o LLM** ao usuário | Identidade: é "a inteligência da Nidum", não "OpenAI/Anthropic". |
| D8 | **Geração de imagem via Gemini** (`imagen-4.0-generate-001`, predict) | O modelo padrão do Open WebUI dava 404; este funciona com billing pago. |
| D9 | **Tríade fonte/forma/fluxo só quando aplicável** (gate no classificador) | Respostas pareciam "treinamento corporativo". A tríade é da própria Fonte (*Silêncio, Vida e Liberdade*), mas só cabe em pedidos gerativos. |
| D10 | **Editorial: estender o fork, headless (API+chat), Storage S3 ao escalar** | Precisa de endpoints/DB/jobs; livros estouram o volume de 500 MB. |
| D11 | **Editorial: evitar libs AGPL** (PyMuPDF, ebooklib) | Risco para uso comercial; EPUB é montado/lido com zipfile+XML. |
| D12 | **Continuidade: tudo no nome da empresa, chaves no Bitwarden** | A operação precisa sobreviver à saída de qualquer pessoa. |
| D13 | **Migração de e-mail adiada** | Tudo está no `nidum.tec26@gmail.com` (provisório) até haver e-mail institucional. Recomendação aceita: usar e-mail genérico de função, não pessoal. |
| D14 | **Ibrand para títulos** (além do logotipo) | Decisão do usuário (o brandbook reserva Ibrand ao logotipo, mas foi sobreposto); Ibrand tem cobertura PT completa. |

## Parte 2 — Pendências que precisam de decisão ou ação

### Prioridade definida pelo usuário
1. ✅ **Separação de memória (Postgres)** — CONCLUÍDA em 2026-07-02 (Postgres + pgvector + R2). Ver [07_Diario_e_Status](07_Diario_e_Status.md).
2. 🟠 **Volume / billing do Railway** — o volume antigo segue montado como backup; avaliar desmontá-lo após período de segurança. Billing OK ($3/$20).
3. 🟡 **Grupos / permissionamento** — controle de acesso mais fino (plano esboçado: grupos Externo/Interno, base pública sem v30).

### Retenção de conversas (spec decidida 2026-07-02 — a IMPLEMENTAR)
- **Objetivo:** gestão de armazenamento.
- **Regra 1 — comprimir:** chat **sem interação há 7 dias** → comprimir o conteúdo para ocupar menos espaço.
- **Regra 2 — deletar:** chat **sem interação há 90 dias** → deletar o chat **+ os arquivos associados**.
- **Natureza:** funcionalidade nova de backend (Open WebUI não tem nativo) — job agendado sobre a tabela `chat` do Postgres, com **dry-run** antes de qualquer exclusão. A parte dos 90 dias é destrutiva → backup/confirmação.
- **Decisão em aberto:** "comprimir" = compressão real do conteúdo (exige o app descomprimir na leitura, mexe no fork) **ou** arquivar (nativo, mais simples). A decidir antes de implementar.

### Outras pendências em aberto
| Pendência | Natureza | Observação |
|---|---|---|
| **Default de `BASE_CONHECIMENTO_ID`** aponta para base morta (`f2c8a48c`) | Dívida técnica | Só funciona porque a valve sobrescreve para `a85d8a8f`. Alinhar o default no código. |
| **PDFs órfãos do v29/v30** (cópias fora da base do ChatND) | Decisão | Mantidos por regra `#não exclua nada`; remover só com OK explícito. |
| **`Capture001.png` (9,45 MB)** no volume | Decisão | Não removido (screenshot ambíguo, possível anexo de chat). |
| **Mecanismo de higiene de duplicados recorrente** | Implementação | **Desenhado** em `_nidum_manutencao/HIGIENE_DUPLICADOS.md`, não implementado (em stand-by por decisão do usuário). |
| **Editorial F3 — vínculo "modelo por projeto"** | Implementação + deploy | Núcleo da ficha pronto; falta o manifold no seletor. |
| **Editorial F2.4b — imagens nos exports** | Implementação | Embutir imagens com alt-text nos `.docx/.epub/.pdf`. |
| **`origin/main` atrás do main local** | Sincronização | Um deploy foi via `railway up` do local; sincronizar o GitHub com `git push origin main`. |
| **Repasse no roteador** (rota documentos sem trecho relevante deveria cair para diaadia) | Implementação | Hoje, sem contexto relevante, ainda manda para Documentos sem handoff. |
| **Sobreposição rápido × dia a dia** | Decisão | Fronteira tênue; usuário cogitou afiar ou fundir. |
| **SharePoint como fonte (auto-update)** | Projeto futuro | Exige app no Azure AD + Microsoft Graph + job de sync. |
| **Modelo guard de input/output** | Segurança | Recomendado antes de abrir uploads/conteúdo externo (injeção indireta). |

> Conforme as decisões forem tomadas, mover da Parte 2 para a Parte 1 (com a data e o porquê).
