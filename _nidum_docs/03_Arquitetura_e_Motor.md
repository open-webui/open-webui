# 03 — Arquitetura e Motor

> **Para quem é:** quem precisa entender como o sistema pensa por dentro — para alterar o comportamento, debugar ou avaliar uma proposta técnica.
> **Quando consultar:** antes de mexer no roteador, na busca ou na geração de arquivos.

> ## ⏱️ Última verificação contra o código e o painel: **16/07/2026**
>
> **Como este documento foi escrito:** cada afirmação estrutural abaixo foi **conferida no código ou no painel de produção nesta data**. O que não pôde ser provado **não foi escrito**.
>
> **Como usar isto:** quanto mais longe você estiver de 16/07/2026, **menos confiável** este documento é. Se a data acima estiver velha e você for decidir algo com base aqui, **confira antes** — o comando de verificação está ao lado de cada afirmação.
>
> **Por que o aviso existe:** a versão anterior deste documento errava **todos** os fatos estruturais — apontava para um arquivo que não existe, uma versão 18 números atrás, uma coleção aposentada e um modo de busca desligado havia semanas. Ela não nasceu errada: **apodreceu em silêncio**, porque nada obrigava a conferi-la. **Doc que mente com autoridade é pior que doc nenhuma** — por isso esta foi reescrita do zero, e não corrigida.

---

## O que o sistema é

```
        Usuário (chatnd.nidumbrasil.com.br)
                     │
        Open WebUI (fork, v0.9.6)          <- o chassi: login, chat, upload, colecoes
                     │
          Função Pipe "ChatND"  1.28.0     <- o motor (codigo Nidum)
                     │  classifica e encaminha
   ┌────────┬────────┼─────────┬──────────┬─────────┐
 rápido  dia a dia  documentos  raciocínio  arquivo  imagem
                     │                        │        │
                busca na base            ferramenta  Gemini
               (2 coleções)              de arquivos
```

- **Open WebUI (o fork):** login, usuários, upload, armazenamento e a infraestrutura de chat. É o **chassi**.
- **ChatND (o motor):** uma **Função Pipe** que aparece como um "modelo" no seletor, mas na verdade **classifica e redireciona**. É **aditiva** — não altera os motores, só os orquestra.
- **Motores wrapper:** modelos customizados (`base model` + `system prompt`), privados. Só o ChatND aparece ao usuário comum.

**Código-fonte do motor:** `_nidum_tools/chatnd.py` — **versão 1.28.0**.
*Verifique:* `grep -m1 "^version:" _nidum_tools/chatnd.py`

---

## O caminho de uma mensagem

1. O usuário manda uma mensagem para o "modelo" **ChatND**.
2. O ChatND chama um **classificador** — `gpt-5-mini` (valve `ROUTER_MODEL`) — que lê as últimas ~6 mensagens e devolve **uma** categoria: `imagem`, `arquivo`, `documentos`, `raciocinio`, `rapido` ou `diaadia`.
3. **Guarda determinístico:** se a categoria for `rapido` ou `diaadia` **e** a mensagem tiver marca temporal (`reunião`, `ata`, `quando`, uma data…), ela é **forçada para `documentos`**.
   **Existe porque o classificador errava exatamente aqui** — mandava *"reunião de 08/07"* para `rapido`, e a pergunta nunca chegava à base.
   *No código:* `chatnd.py:1839`
4. Conforme a categoria:
   - **imagem** → gera via Gemini (motor oculto) e devolve com legenda.
   - **arquivo** → busca contexto + monta a estrutura com `gpt-5.1` + chama a ferramenta de arquivos → link de download.
   - **documentos** → **busca na base** e injeta os trechos antes de encaminhar ao motor *Documentos*.
   - **raciocinio / rapido / diaadia** → encaminha direto ao motor correspondente.
5. O motor de destino responde; a resposta volta ao usuário.

**A rota vai para o log, sempre:** `chatnd: roteador -> <categoria> (classificador=<saída>)`.

---

## A base de conhecimento: **duas coleções**

| Coleção | Id | O que tem |
|---|---|---|
| **ND - Fonte (Fundadores)** | `705ca6ca-7f8a-4352-8004-4ee41f72b5ab` | A pasta `FONTE/` do repositório da esteira |
| **ND - Acervos Institucionais** | `9ce06025-7b38-4b73-b225-b22932e6e73a` | **Todas as demais** pastas (`ACERVOS/`, `MKT/`, `JUR/`, `TEC/`, …) |

*Verifique:* `_scripts/sync_config.json`, **no repositório `nidum-chatnd-basefonte`** — é lá que os ids são a fonte da verdade, **não aqui**. Esta tabela é cópia, e cópia envelhece.

**Quem enche as coleções:** a **esteira**, a cada 6 horas, a partir do SharePoint. **Ninguém sobe arquivo à mão.**

**O ChatND consulta as duas na mesma chamada.** A valve `BASE_CONHECIMENTO_ID` aceita os dois ids separados por vírgula ou espaço; o pipe filtra por permissão do usuário e faz **uma única** chamada de busca, com `k` **global** — as duas coleções **competem entre si** pelas mesmas vagas.

---

## Como a busca funciona

| Parâmetro | Valor em 16/07/2026 | Onde se configura |
|---|---|---|
| Busca híbrida | **ligada** | Admin → Settings → Documents |
| Reranker | **`BAAI/bge-reranker-base`** | idem |
| Peso do BM25 | **0,5** | idem |
| **Top K** | **24** | idem |
| **Top K Reranker** | **24** | idem |
| **Relevance Threshold (`r`)** | **0** | idem |
| Enriquecer o texto da pesquisa híbrida | **ligada** | idem |
| Embedding | **OpenAI `text-embedding-3-small`** — **não é local** | idem |

*Verifique o embedding:* o log de produção traz, em todo chunk recuperado, `embedding_config: {'engine': 'openai', 'model': 'text-embedding-3-small'}`.

### Três coisas que não são óbvias

**1. `r=0` é deliberado — subir esse número quebra a busca por data.**
O `r` descarta chunks abaixo do score. Parece prudente subir para 0,2–0,3. **Seria pior que inútil:** os chunks da ata de 13/07 pontuam **0,244 e 0,266**. Um piso de 0,3 os descartaria — e a pergunta que motivou toda a investigação voltaria a falhar. **Medido, não suposto.**

**2. A expansão de datas depende de uma valve do Admin.**
O ChatND detecta datas na pergunta e **anexa as variantes** ao texto de busca (`13/07` → `13072026`, `2026-07-13`, `13 de julho de 2026`…), porque o BM25 casa **token a token** e o embedding **não entende calendário**.
**Isso só paga se a valve "Enriquecer o texto da pesquisa híbrida" estiver LIGADA** — é ela que põe o **nome do arquivo** no texto que o BM25 enxerga. **São duas metades da mesma ponte.** Desligar a valve regride a busca por data **sem que o sintoma aponte para o toggle**.
*No código:* `_expandir_datas()`, aplicada dentro de `_buscar_sources` — **não** no `_texto_de_busca`, que também alimenta a rota de imagem.

**3. O reranker é semântico: ele não "vê" datas.**
É um cross-encoder — entende **assunto**, não **calendário**. A expansão de datas põe o documento no **pool de candidatos** (via BM25), mas quem decide o score final é o reranker. Por isso a expansão era **necessária mas não suficiente**, e por isso o `r=0` importa.

---

## Documento inteiro: **aposentado**

O ChatND **não injeta mais documentos inteiros**. A valve `MAX_DOCS_INTEIROS` tem default **`0`** — só os **trechos** recuperados pela busca entram no contexto.

**Por quê:** o documento inteiro competia com a busca afinada e **estourava o orçamento**. Log real: **159.849 de 200.000** caracteres consumidos por 3 documentos inteiros, sobrando **zero** para o resto.

*No código:* `chatnd.py:1067`

---

## Fundadores: **sem privilégio de arquitetura**

**Decisão da governança, validada por medição:** os Documentos Fundadores **não têm tratamento especial**. Eles entram na resposta **quando a busca os acha por relevância** — como qualquer outro documento.

**A prova:** as 5 perguntas fundadoras do banco (P9–P13) **passam com o privilégio desligado**, todas citando o Documento Fundador **com a versão**. O mecanismo era **peso morto**.

**E o custo dele era real:** numa pergunta 100% operacional — *"a decisão de 13/07 está alinhada com o combinado?"* — o mecanismo injetava **120.000 caracteres** de v29+v30, só porque a palavra "alinhada" contém `alinhad`. Na mesma busca, os chunks da Fonte pontuaram **0,0048 / 0,0034 / 0,00028**: **o rankeador já dizia que a Fonte não tinha nada a ver com a pergunta — e o mecanismo passava por cima.**

**O que sobrou, e em que estado:**

| Valve | Default | O que faz |
|---|---|---|
| `FUNDADORES_INTEIROS_SE_GATILHO` | **`False`** | O mecanismo acima. **Desligado.** |
| `ANCORA_FUNDADORES_SE_BUSCA_VAZIA` | **`True`** | **Coisa diferente:** se a busca voltar **vazia**, ancora nos fundadores em vez de responder sem base nenhuma. Rede de segurança — só dispara quando não há alternativa. |

*No código:* `chatnd.py:1086` e `1091`

**No log**, o campo `piso` diz **qual** ramo disparou: `gatilho` | `busca-vazia` | `off`. **`busca-vazia` recorrente é alarme:** significa que a busca está voltando sem nada.

> ⚠️ **Valve é persistida no banco.** O default do código **só vale na primeira carga**. Para saber o valor real de qualquer valve, **olhe o painel — não o código.**

---

## Como o código chega à produção — **dois caminhos diferentes**

| O que | Como | Efeito |
|---|---|---|
| **Backend** (`backend/`, `editorial/`, `Dockerfile`) | **`git push` → Railway** | Auto-deploy **ligado**, branch `main` do repositório **`nidum-oficial-tec/nidum-platform`**. **Com downtime.** |
| **Pipe e Tools** (`_nidum_tools/*.py`) | **API do Open WebUI** (`/api/v1/functions/id/chatnd/update`) | **Manual.** Existe `_nidum_manutencao/publicar_tool.py` |

> ⚠️ **A consequência mais importante deste documento:** **mergear na `main` não publica o pipe.** O `chatnd.py` do repositório e o `chatnd.py` que está rodando podem estar em versões diferentes — e já estiveram. **Para saber o que está no ar, olhe o painel.**

> ⚠️ **Ao republicar só uma tool, republique também o pipe** — isso reseta o cache da tool.

---

## O que está instalado hoje (painel, 16/07/2026)

### Functions

| Nome | Tipo | Versão | Estado |
|---|---|---|---|
| ChatND | **Pipe** | 1.28.0 | enabled |
| Roteador Semantico — Fonte e Convergências | **Filter** | 0.2.0 | **desabilitado** — em processo de remoção |

### Tools, e a quais modelos estão anexadas

| Tool | Anexada a |
|---|---|
| Gerador de Arquivos Nidum | Rápido, Dia A Dia |
| Relatorio de Ambientes Nidum (id `relatorio_ambientes_nidum`, v1.2.0) | Identificador De Ambientes |
| SharePoint Nidum | Identificador De Ambientes |
| Chico - A Fonte · Nidum Convergir · Nidum Convergências | **Chico** |

**Uma tool só age se estiver anexada a um modelo.** Instalada e não anexada = nunca dispara.

### Modelos (wrappers)

| Modelo | Base model |
|---|---|
| Nidum 1.0 - Rápido | `gpt-5-mini` |
| Nidum 1.0 - Dia A Dia | `gpt-5.1` |
| Nidum 1.0 - Documentos | `sonnet-4-6` |
| Nidum 1.0 - Raciocinio | `sonnet-4-6` |
| NIDUM 1.0 - Identificador De Ambientes | `opus-4-8` |
| **Chico** | **`chatnd`** |

*Verifique:* Admin → Functions · Workspace → Tools · Admin → Models.

> **O modelo "Chico" usa o `chatnd` como base model** — as mensagens dele passam pelo nosso roteador. É projeto de outro colaborador, e a **doutrina dele vive nas tools dele**, não no `chatnd.py`.
> **Consequência prática:** mudar as **categorias do roteador** afeta o Chico. Mudar o resto do pipe, não.

---

## Como se prova que uma mudança não quebrou nada

**O banco de perguntas** — `testes/banco_perguntas_chatnd.md`, no repositório `nidum-chatnd-basefonte`. 20 perguntas, rodadas **antes e depois** de toda mudança de busca ou de system prompt.

**Placar em 16/07/2026: 18 OK · 1 PARCIAL · 0 FALHOU.**

**Regra:** queda no placar = reverta e investigue. **Nenhuma mudança de recuperação ou de prompt entra sem passar por aqui.** Ele já matou duas hipóteses plausíveis que teriam piorado o sistema — inclusive a de subir o `r`.

---

## Limitação conhecida

O índice BM25 é **reconstruído do zero, com a coleção inteira, a cada pergunta** (`backend/open_webui/retrieval/utils.py:382`). Com ~86 documentos é irrelevante — faz parte dos ~7 s atuais. **Escala com o tamanho da base:** quando ela crescer, o gargalo será esse, e não o reranker. **Não tratado.**
