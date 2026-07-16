# Rollback do deploy do ChatND (pipe 1.21.0 + valve + wrapper)

Este deploy muda **três** coisas juntas — reverter exige voltar as **três** (reverter só uma deixa o sistema incoerente: ex.: pipe novo lendo duas coleções, mas prompt velho com etiquetas antigas).

## ANTES de aplicar — capture as fontes de rollback (30 segundos)
No painel, **copie e salve localmente** o estado atual, antes de colar qualquer coisa:

1. **Código do pipe atual** — Admin → Functions → **ChatND** → selecione TODO o código → cole num arquivo local `chatnd_ANTES.py`. **Esta é a fonte de rollback mais segura** (é exatamente o que está no ar).
2. **Valor atual da valve** — Admin → Functions → ChatND → Valves → **`BASE_CONHECIMENTO_ID`** → anote o valor (hoje deve ser só `9ce06025-7b38-4b73-b225-b22932e6e73a`, a ACERVOS).
3. **System prompt atual do wrapper** — Workspace → Models → **`nidum-10---documentos`** → System Prompt → cole o texto num arquivo local `prompt_ANTES.md`.

## ⚠️ Valves que exigem ação MANUAL (o código não consegue mudar sozinho)
O Open WebUI **persiste o valor das valves no banco** — mudar o *default* no código **não altera** uma instalação que já tem valor salvo. Depois de republicar, confira em **Admin → Functions → ChatND → Valves**:

| Valve | Valor certo | Por quê |
|---|---|---|
| `BASE_CONHECIMENTO_ID` | `9ce06025-…,705ca6ca-…` | as **duas** coleções (ACERVOS,FONTE) |
| `TOP_K_DOCUMENTOS` | **`0`** | 0 = **herda o Top K do Admin**. Se ficar em `10`, ele **sobrepõe o Admin em silêncio** (foi o que aconteceu: Admin em 24, pipe usando 10) |
| `MAX_DOCS_INTEIROS` | **`0`** | documento inteiro **aposentado** (competia com a busca e estourava o orçamento). `>0` religa |

## Onde pegar a versão anterior do `chatnd.py` (git, alternativa)
A última versão mergeada antes deste pacote está em `origin/main` (era **1.18.0**):
```bash
cd nidum-platform
git show origin/main:_nidum_tools/chatnd.py > chatnd_1.18.0.py
```
⚠️ **Ressalva:** se o pipe no ar tiver sido editado à mão no painel e divergir da `main`, a verdade do rollback é a **cópia do passo 1**, não a `main`. Use o git só se tiver certeza de que o pipe no ar == `origin/main`.

## Quando reverter (sintomas)
- Roteador pior (perguntas que funcionavam voltam a cair em resposta genérica).
- `[Fora do acervo]` em pergunta que antes respondia; respostas vazias ou erro.
- Fundador voltando a abafar atas (operacional vindo com doutrina/`[Fonte + Acervos]` sem motivo).
- Latência muito pior.

## Como reverter (as três, nesta ordem)
1. **Pipe:** Admin → Functions → ChatND → colar `chatnd_ANTES.py` → **Save**.
2. **Valve:** `BASE_CONHECIMENTO_ID` → voltar ao valor anterior (só a ACERVOS: `9ce06025-7b38-4b73-b225-b22932e6e73a`) → **Save**.
3. **Wrapper:** `nidum-10---documentos` → System Prompt → colar `prompt_ANTES.md` → **Save**.

## Verificar que o rollback pegou
Reperguntar, em **chat novo**, algo que já funcionava antes — ex.: *"quais os assuntos da reunião de coautores de 13/07?"* — e conferir que voltou ao comportamento anterior.

## Notas
- Rollback = voltar ao estado de ontem (**uma** coleção, roteador antigo, piso incondicional — que ficava mascarado porque a ACERVOS não tinha os fundadores). É seguro: **nada é apagado**; muda-se só qual coleção o pipe lê e os textos dos prompts.
- As coleções FONTE/ACERVOS no Open WebUI **não** são tocadas pelo rollback (continuam populadas pela esteira).
- Reverter o pipe pela URL do PR/commit não é necessário — o painel é a fonte de verdade do que está no ar.
