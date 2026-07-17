# 03 — Arquitetura e Motor

> **Para quem é:** quem precisa entender como o sistema pensa por dentro — para alterar o comportamento, debugar ou avaliar uma proposta técnica.
> **Quando consultar:** antes de mexer no roteador, na busca ou na geração de arquivos.

> ## ⏱️ Última verificação contra o código e o painel: **16/07/2026**
>
> ### 🚧 Este documento descreve a **1.31.0**, que pode ainda NÃO estar publicada
>
> **Mergear na `main` não publica o pipe** (ver "Como o código chega à produção"). Se o painel mostrar uma versão **anterior à 1.31.0**, este documento descreve **o desenho aprovado, não o que está rodando** — e a diferença é grande: a 1.31.0 funde `rapido`/`diaadia`/`raciocinio` em `geral` e adiciona a trava de menção a Nidum.
>
> **Este aviso sai quando a 1.31.0 for publicada.** Ele existe porque a versão anterior deste documento apodreceu exatamente assim: descrevendo um desenho que a produção não tinha.
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
        Open WebUI (fork, v0.9.6)     <- o chassi: login, chat, upload, colecoes
                     │
          Função Pipe "ChatND"        <- o motor (codigo Nidum)
                     │
       classificador: e da Nidum?
                     │
      ┌──────────────┴───────────┬──────────┬────────┐
  documentos                   geral     arquivo   imagem
  (SIM: e da Nidum)      (NAO: e fora)      │         │
      │                          │      ferramenta  Gemini
  busca na base          web (SO esta     de arquivos
  (2 colecoes)                rota)
  NUNCA ve web
```

**Um eixo por vez:** ou é da Nidum (`documentos` — com base, **sem web**), ou não é (`geral` — com web, **sem base**). Ferramentas (`imagem`, `arquivo`) à parte.

- **Open WebUI (o fork):** login, usuários, upload, armazenamento e a infraestrutura de chat. É o **chassi**.
- **ChatND (o motor):** uma **Função Pipe** que aparece como um "modelo" no seletor, mas na verdade **classifica e redireciona**. É **aditiva** — não altera os motores, só os orquestra.
- **Motores wrapper:** modelos customizados (`base model` + `system prompt`), privados. Só o ChatND aparece ao usuário comum.

**Código-fonte do motor:** `_nidum_tools/chatnd.py`.
*Verifique a versão:* `grep -m1 "^version:" _nidum_tools/chatnd.py` — **e confira no painel qual está publicada**, que pode ser outra (ver "Como o código chega à produção").

---

## O caminho de uma mensagem

1. O usuário manda uma mensagem para o "modelo" **ChatND**.
2. O ChatND chama um **classificador** — `gpt-5-mini` (valve `ROUTER_MODEL`) — que lê as últimas ~6 mensagens e devolve **uma** de **quatro** categorias: `imagem`, `arquivo`, `documentos` ou `geral`.
3. **Duas travas determinísticas** corrigem o classificador quando ele erra (detalhe abaixo).
4. Conforme a categoria:
   - **imagem** → gera via Gemini (motor oculto) e devolve com legenda.
   - **arquivo** → busca contexto + monta a estrutura com `gpt-5.1` + chama a ferramenta de arquivos → link de download.
   - **documentos** → **busca na base** e injeta os trechos. **Nunca toca a web.**
   - **geral** → **busca na web** e injeta os resultados. **Nunca toca a base.**
5. O motor de destino responde; a resposta volta ao usuário.

**A rota vai para o log, sempre:** `chatnd: roteador -> <categoria> (classificador=<saída>)`.

### A fronteira, e por que ela tem trava

**Todo o desenho depende de UMA decisão:** *"isto é sobre a Nidum?"* Por isso ela é a única coisa do sistema com rede de segurança.

**Os dois erros não custam o mesmo — e a assimetria define o default:**

| Erro | Custo |
|---|---|
| Falso positivo (mandar para a base algo que não é da Nidum) | **~1 s de busca vazia.** O motor responde `[Fora do acervo]` e a conversa segue |
| **Falso negativo** (mandar para `geral` algo **que é** da Nidum) | **Resposta do Google sobre uma empresa homônima**, com confiança e citação. **Erro silencioso** |

> **Regra: na dúvida, base.** Está escrita no prompt do classificador *e* garantida por duas travas.

**As duas travas são determinísticas de propósito — elas têm que funcionar exatamente quando o classificador não está funcionando** (inclusive quando ele falha e o padrão vira `geral`):

| Trava | Dispara quando | Nasceu de |
|---|---|---|
| **Marca temporal** | a mensagem tem data, "reunião", "ata", "convergência", "quando" | **bug real**: *"reunião de 08/07"* foi para conversa e nunca chegou à base |
| **Menção a Nidum** | a pessoa escreveu a **palavra** `Nidum` | o pior caso: *"qual o propósito da Nidum?"* indo para a internet |

*No código:* `_tem_marca_temporal` e `_menciona_nidum`. **Testadas** em `_nidum_tools/teste_travas.py`.

> ⚠️ **Buraco conhecido e aceito:** pergunta institucional **sem** a palavra "Nidum" e **sem** marca temporal — *"como funciona o EGP aqui?"* — depende **só do classificador**. As travas não alcançam. Está registrado como caso que passa no `teste_travas.py`, para ficar visível.
>
> **Por que não cobrir apelidos** ("a casa", "aqui", "a rede"): trava que adivinha deixa de ser trava e vira palpite. Isso é juízo — e juízo é do classificador.

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

## A web: **só a rota `geral`, e só o pipe aciona**

**A rota `geral` busca na internet. A rota `documentos` nunca vê conteúdo da web.** Não é preferência de estilo — é o que impede *"qual o propósito da Nidum?"* de ser respondido com uma empresa **homônima** achada no Google.

### Por que a ordem importa: **primeiro classifica, depois busca**

O Open WebUI tem um web search **próprio**, que roda **antes** do pipe (dentro do `process_chat_payload`) e é **cego ao contexto**: se ligado, busca em **toda** pergunta e injeta o resultado nas mensagens. **O pipe não tem como impedir** — quando ele acorda, já aconteceu.

Por isso esse caminho fica **desligado**, e o **pipe** é quem aciona a web — **depois** de saber que a pergunta não é da Nidum.

### A defesa tem duas camadas — as duas precisam ficar como estão

| Camada | Estado | Impede |
|---|---|---|
| Permissão do grupo *"Pesquisa na Web"* | **OFF** | o **botão** aparecer para o usuário |
| `ENABLE_WEB_SEARCH` | **`False`** | o **middleware** e o endpoint `/process/web/search` |

> 🚨 **`ENABLE_WEB_SEARCH=False` com o ChatND buscando na web NÃO é bug.** O pipe chama a camada de baixo — **`search_web()`** — que não olha essa variável nem a permissão. **Ligar a variável reabre o caminho pré-pipe e quebra a garantia.** Detalhe completo em [04_Dicionario](04_Dicionario_de_Dados_e_Configuracao.md).

**Por que pular esses gates não é burlar segurança:** a permissão `features.web_search` significa *"o **usuário** pode ligar o toggle"*. **O pipe não é o usuário — é o sistema decidindo.**

**Buscador:** `duckduckgo` — sem chave, sem cadastro, sem custo. Trocar é mudar uma variável; o código não muda.

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
| ChatND | **Pipe** | ver painel | enabled |
| Roteador Semantico — Fonte e Convergências | **Filter** | 0.2.0 | **desabilitado** — em processo de remoção |

### Tools, e a quais modelos estão anexadas

| Tool | Anexada a |
|---|---|
| Gerador de Arquivos Nidum | o wrapper da rota `geral` |
| Relatorio de Ambientes Nidum (id `relatorio_ambientes_nidum`, v1.2.0) | Identificador De Ambientes |
| SharePoint Nidum | Identificador De Ambientes |
| Chico - A Fonte · Nidum Convergir · Nidum Convergências | **Chico** |

**Uma tool só age se estiver anexada a um modelo.** Instalada e não anexada = nunca dispara.

> **Por isso a rota `geral` reaproveita o wrapper do antigo "Dia A Dia"** em vez de ganhar um novo: o Gerador de Arquivos **já está anexado a ele**. Criar wrapper novo exigiria lembrar de reanexar a tool — e é o clique que ninguém lembra.

### Modelos (wrappers)

| Modelo | Base model | Papel |
|---|---|---|
| wrapper da rota **`geral`** (era "Nidum 1.0 - Dia A Dia") | **`sonnet-4-6`** | Fora do contexto Nidum |
| Nidum 1.0 - Documentos | `sonnet-4-6` | Contexto Nidum, com base |
| NIDUM 1.0 - Identificador De Ambientes | `opus-4-8` | Relatório de ambientes |
| **Chico** | **`chatnd`** | Projeto de outro colaborador |

> **`geral` é Sonnet, não um modelo "mini" — e isso foi medido, não estimado.** Testado com `gpt-5-mini`: ele **errou as definições de SPE e SCP** — as duas — e construiu **duas páginas** de tabelas, diagramas e exemplos "reais" em cima do erro. Articulado, confiante, falso. **E SPE × SCP é o tema da ata de 08/07**: um coautor perguntaria e receberia consultoria inventada sobre uma decisão **real** da Nidum. Um tema pode estar "fora do contexto Nidum" e a resposta ainda entrar numa decisão da Nidum. **Rebaixar o modelo de `geral` reabre isso.**

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
