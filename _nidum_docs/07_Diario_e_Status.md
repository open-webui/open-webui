# 07 — Diário e Status

> **Para quem é:** quem precisa saber **onde o projeto está hoje** — o que está pronto, em andamento, bloqueado.
> **Quando consultar:** ao retomar o trabalho ou planejar a próxima sessão.
> **Como manter:** este é um registro **vivo e datado**. A cada sessão relevante, **acrescentar** uma entrada nova no topo do histórico — **nunca apagar** o que já está escrito.

> **Referência cruzada (decisão de 2026-07-10, opção b):** este é o diário oficial da
> **PLATAFORMA** (ChatND / Open WebUI — código das funções, deploy, runbooks). O
> projeto da **ESTEIRA** (SharePoint → base de conhecimento) tem o seu **próprio**
> registro oficial em `nidum-chatnd-basefonte/_docs/REGISTRO_TRABALHO.md`. São **dois
> registros distintos de propósito** — cada um é a fonte da verdade do seu escopo;
> nenhum vira ponteiro do outro.

---

## Sessão 2026-07-16 (noite) — A reforma: 6 rotas viram 4, e a web entra pela porta certa

### O que mudou (1.29.0 → 1.31.0)

| Versão | O quê |
|---|---|
| **1.29.0** | Arranca a **doutrina morta**: `_docs_prioritarios`, o ramo do gatilho, a valve órfã |
| **1.30.0** | Hotfix: `raciocinio` respondia sobre a Nidum **sem base**, e a tríade mandava ancorar nos fundadores que ele não carregava |
| **1.31.0** | **Fatias 1+2**: `rapido`+`diaadia`+`raciocinio` → **`geral`**; trava de **menção a Nidum**; `teste_travas.py` |

### `raciocinio`: peso morto **medido**, não suposto

**Grep no log de um dia inteiro de uso + dezenas de testes: ZERO ocorrências de `roteador -> raciocinio`.** A rota existia e **nunca era escolhida** — o `documentos` do classificador é amplo demais para deixar passar.

**Isso encerra o bug da tríade como "existe no código, nunca disparou".** Ele some junto com a rota, na 1.31.0. A 1.30.0 vira quase redundante — só faria sentido se fosse para o ar **antes** da reforma, e o grep provou que não há pressa.

### A decisão que reordenou tudo: **`geral` é Sonnet, não Haiku**

O desenho inicial rebaixava "fora de contexto" para Haiku. **O Davi recusou — e foi medir.** `gpt-5-mini` **errou as definições de SPE e SCP** — as duas — e construiu **duas páginas** de tabelas, diagramas e exemplos "reais" (3M, Magazine Luiza) em cima do erro. Articulado, confiante, falso. O Sonnet acertou, com os artigos do Código Civil.

> **O agravante que decidiu:** **SPE × SCP é o tema da ata de 08/07** — o Daniel apresentou essa comparação para estruturar a participação de investidores. Um coautor perguntaria e receberia **consultoria inventada sobre uma decisão real da Nidum**. **O tema está "fora do contexto Nidum", mas a resposta entra numa decisão da Nidum.** Era um erro silencioso por uma porta que íamos abrir sozinhos.

### Web: a ordem invertida, e por que a `ENABLE_WEB_SEARCH` fica `False`

**Hoje:** o web search do Open WebUI roda **antes** do pipe, **cego ao contexto** — se ligado, contamina até pergunta institucional, e **o pipe não pode impedir**.

**Novo:** o pipe **classifica primeiro** e só então decide. **Só a rota `geral` toca a web.**

**Defesa em duas camadas** (as duas ficam): permissão do grupo **OFF** (impede o botão) + `ENABLE_WEB_SEARCH=False` (impede middleware e endpoint). **O pipe chama `search_web()`**, a camada de baixo, que não olha nenhum dos dois.

> **Por que isso não é burlar segurança:** `features.web_search` significa *"o **usuário** pode ligar o toggle"*. **O pipe não é o usuário — é o sistema decidindo.**

**A sonda foi decisiva — e o resultado dela mudou o plano.** Ela provou que o import funciona (`[OK] passo 0`) e que o 403 era **config, não impossibilidade**. Mas, ao investigar o 403, apareceu o que eu **não** tinha visto: **a permissão do grupo é checada DENTRO do `process_web_search`** (`routers/retrieval.py:2222`), não só na interface. **A defesa que eu tinha proposto (permissão OFF) mataria o próprio pipe** — 403 para todo coautor. **A desconfiança do Davi na pergunta 4 achou o buraco.** A saída (`search_web`, a camada de baixo) só apareceu porque a sonda forçou a leitura.

**Engine: `duckduckgo`** — sem chave, sem cadastro, sem custo. **Decisão registrada:** não faz sentido escolher pago antes de saber se o grátis resolve perguntas factuais de volume baixo. Trocar é uma variável.

> **⚠️ Erro meu, registrado para não se repetir:** meu primeiro levantamento dos engines marcou **9 como "sem chave"** — `bing`, `azure`, `jina`, `yandex`, `firecrawl`, `external`, `youcom`, `perplexity`, `sougou`. **Todos exigem chave.** O regex não pegava o formato da condição deles. **Se a lista errada tivesse ido, o Bing seria escolhido como "grátis".** Conferi um a um antes de entregar. **Ao reconferir um engine, leia o bloco `elif engine == '<nome>'` — não confie em busca por padrão.**

### Duas correções minhas de estimativa

1. **Custo da fatia 3: eu disse "o pipe teria que carregar as páginas".** Errado — **para mais**. O `SearchResult` já traz `snippet`, e o próprio fork tem o caminho que usa só isso (`BYPASS_WEB_SEARCH_WEB_LOADER`). **Não há scraping: ~30–40 linhas, não 300.**
2. **A regra da tríade no classificador: eu disse 1.247 caracteres (31% do prompt).** São **518 (13%)**. Meu script quebrou o prompt por `". "` e capturou frases vizinhas. **Inflei 2,4×** — e a aprovação do enxugamento veio em cima desse número. **Cancelado.**

### 📌 O achado da semana virou REGRA no `CLAUDE.md` — não ficou como anedota

**A doc `03_Arquitetura`, reescrita do zero HOJE para consertar apodrecimento, descrevia 6 rotas — e a fatia 1 fez 4. Ela apodreceu antes de mergear.** Em horas.

**Isso não é ironia — é diagnóstico.** É a prova de que o apodrecimento das docs **não era falta de disciplina**. Havia uma regra no `CLAUDE.md`, obrigatória, e ela era:

> *"Atualize `Documentacao_ChatND_Nidum.html` na **MESMA sessão da alteração**"*

**"Alteração" não é "deploy".** Aqui pipe/tools vão por **API, manualmente** — **mergear na `main` não publica**. Então a doc atualizada "na mesma sessão da alteração" fica **certa sobre algo que ainda não existe** e **errada sobre o que está no ar**.

> ### **O problema não era ninguém seguir a regra. Era segui-la.**

**A regra nova, escrita no `CLAUDE.md`** (onde regras moram e são lidas toda sessão, não aqui — diário é log, e regra que mora em log é anedota bem escrita):

> **Doc que descreve PRODUÇÃO mergeia junto com o DEPLOY — nunca antes.**
> Doc de **decisão** (este diário, o `08_Decisoes`) mergeia quando a decisão é tomada — **decisão não espera deploy: ela É o registro de que se decidiu.**
> **Na dúvida:** *"isto fica falso se o publish não acontecer?"* Se sim, espera o deploy.

**E o carimbo `Última verificação: <data>`** que a `03` passou a ter: ele **não impede** o apodrecimento — **deixa ele visível**. Era exatamente o que a doc antiga não tinha: ela mentia com autoridade e **sem data**, então ninguém tinha como saber que estava velha.

## Sessão 2026-07-16 (tarde) — Levantamento do estado real e corte de código morto

**Corte MEDIDO, não suposto.** Registro do método, porque ele é o ponto: nenhuma linha
foi removida por "parecer complexa" ou por argumento de arquitetura. Foi removida porque
**o painel provou que estava morta e o banco provou que ninguém sentia falta.**

### As duas ferramentas que estavam mortas — e ninguém notou

| Ferramenta | Linhas | Evidência **de produção** |
|---|---|---|
| `nidum_fonte_quadro_de_pessoas.py` | **1.286** | Instalada como Tool, **anexada a nenhum modelo** → nunca disparou |
| `roteador_semantico_da_fonte_nidum.py` | **1.544** | Function *enabled*, mas a valve **`api_key` VAZIA** → `if not api_key: return body` (linha 1517). Carregava em toda mensagem, **nunca agiu** |

**A prova não foi argumento — foi o presente:** o sistema que o banco de perguntas mediu
em **18/19** já era o sistema **sem elas**. Depois do corte, **P9/P10/P13 rodaram com as
duas fora: todas OK, comportamento idêntico** — `[Fonte]` e `[Fonte + Acervos]`, citando
v29/v30 com versão, e a **P13 avisou sozinha que a v31 é rascunho**. Zero regressão.

> **O achado do painel que justificou o delete (não só o disable):** as valves do roteador
> mostravam **`Enabled: Ativado`** e **`Api Key: vazia`**. **Duas luzes verdes e nada
> acontecendo.** É uma **bomba de efeito retardado**: bastaria alguém preencher a chave
> "para testar" e um `FONTE_INDEX` **congelado em 2026-06-27** voltaria a injetar
> *"RESPOSTA OFICIAL DO ENGINE… entregue sem resumir"* **por fora da busca** — sem
> reranker, sem citação, sem etiqueta. Desabilitar não bastava.

### O que o `quadro_de_pessoas` fazia que a busca não faz melhor

**Uma coisa: determinismo do roster.** E não compensava, por três motivos, em ordem de
peso: (1) **estava morto e ninguém notou** — se a garantia importasse na prática, a falta
teria aparecido; (2) o determinismo dele era sobre **dado congelado** — *um LLM lendo o
`.md` de hoje erra menos que um dicionário certíssimo sobre ontem*; (3) o conteúdo **já
está na base**, atualizado a cada 6 h pela esteira, com citação e etiqueta
(`FONTE/Nidum_Quadro_de_Pessoas.md`, `FONTE/Grupo_Nidum_Estrutura_e_Direcionamento.md`).

### Estado do corte: ✅ **FECHADO — 2.830 linhas fora**

| Ferramenta | Linhas | Painel | Repo |
|---|---|---|---|
| `nidum_fonte_quadro_de_pessoas` | **1.286** | ✅ deletada (Tools: 8 → 7) | ✅ removido |
| `roteador_semantico_da_fonte_nidum` | **1.544** | ✅ **deletada** — **Functions agora só tem o ChatND** | ✅ removido |

**`_nidum_tools/` ficou com três arquivos:** `chatnd.py`, `gerador_de_arquivos_nidum.py`,
`teste_datas.py`.

**A ordem foi painel → repo, e ela importa:** enquanto o código está instalado, ele **roda
a partir do banco** — apagar do Git não o tira do ar. O contrário é seguro: o Git nunca
perde nada. **Não se remove do repositório código que ainda está instalado em produção.**

**O aval do time foi condição, não formalidade.** O `roteador_semantico` era **filter
global**: tocava **todas** as conversas, inclusive as do **Chico** — projeto de outro
colaborador. Mesmo provado no-op, deletar coisa que atravessa o trabalho alheio **sem
perguntar** é decidir pelos outros. O time confirmou que **ninguém usa** (nem a function,
nem os 3 projetos do Railway).

> **Por que delete, e não apenas disable:** as valves mostravam **`Enabled: Ativado`** e
> **`Api Key: vazia`** — **duas luzes verdes e nada acontecendo**. Enquanto o código
> existisse com a valve vazia, bastava **alguém preencher a chave "para testar"** e o
> `FONTE_INDEX` **congelado em 2026-06-27** voltaria a injetar *"RESPOSTA OFICIAL DO
> ENGINE… entregue sem resumir"* **por fora da busca**. Desabilitado, era **bomba de
> efeito retardado**. Deletado, não é nada.

**A cadeia de evidência, do começo ao fim — nenhum elo foi suposto:**

1. **O log provou que estava vivo:** `Loaded module: function_roteador_semantico_da_fonte_nidum`
   em toda chamada. Ninguém sabia.
2. **O código provou que não agia:** `if not self.valves.enabled or not self.valves.api_key:
   return body` (linha 1517) — e o painel confirmou a `api_key` **vazia**. *Carregado ≠
   agindo.*
3. **O banco provou que ninguém sentia falta:** P9/P10/P13 com as duas fora → **todas OK**,
   comportamento idêntico, citando v29/v30 com versão.
4. **O time provou que ninguém usa.**

**Nenhuma linha saiu por "parecer complexa".** Saíram porque quatro fontes independentes —
log, código, banco de perguntas e pessoas — disseram a mesma coisa.

### A doutrina, que eram DUAS coisas — e só uma era doutrina

**Eu havia listado a tríade ao lado do piso dos fundadores como "doutrina codificada, candidata a corte". Errei** — são coisas de naturezas diferentes, e tratá-las igual teria cortado a errada. O Davi separou as duas, e a separação estava certa.

**A1 — o piso do gatilho: código morto, arrancado.** Virou a 1.29.0 (ver a sessão da noite).

#### A2 — a tríade: **investigada e MANTIDA por decisão** — não reabrir como "doutrina esquecida"

**Ela está VIVA.** Prova: log de produção `chatnd: roteador -> documentos (classificador='documentos | triade')`, e a valve `TRIADE_ATIVA` **Ativado** no painel.

**O que ela é:** não é texto colado em toda resposta. É um **pedido de estrutura, condicionado, decidido por um juiz**. O classificador só acrescenta `| triade` **se** o pedido for sobre **movimento, relação, geração ou transformação** — e **explicitamente NÃO** para **inventário, definição ou fato**. Se marcar, injeta-se o `VOZ_TRIADE` (**704 chars**) pedindo Fonte/Forma/Fluxo — e o próprio texto manda *"deixe a tríade RESPIRAR… NUNCA como três seções fixas carimbadas"*.

**Por que ela NÃO é o piso:**

| | Piso dos fundadores (**removido**) | Tríade (**mantida**) |
|---|---|---|
| Decidia por | **substring** (`alinhad`) | **um juiz avaliando o pedido** |
| Passava por cima de | **o rankeador** (injetava a Fonte a 0,0048) | **nada** — não toca a busca |
| Custo quando dispara | **120.000 chars** | **704 chars** (**170× menos**) |
| Afetava | **o que o modelo VÊ** (conteúdo) | **como o modelo ESCREVE** (forma) |
| Podia responder errado? | **sim** — abafava a ata | **não** — não muda o que foi recuperado |

**A tríade é instrução de voz** — da mesma família de *"responda em português"* ou *"cite a fonte com a versão"*. Não decide **o que é verdade**; decide **como organizar a explicação**. **O piso decidia o que o modelo lia; a tríade decide como ele escreve o que leu.**

> **Decisão do Davi, registrada:** *"a tríade não toca o dia a dia por desenho, e é o único lugar onde está escrito que a Nidum tem uma voz. **Deve soar Nidum**."* **Mantida por decisão, não por inércia.** A queixa original — *"os fundadores poluem o dia a dia"* — era sobre **o piso**, e o piso foi arrancado.

**Enxugamento proposto por mim e CANCELADO — o motivo importa mais que o resultado.** Propus condensar a regra da tríade no classificador alegando **1.247 caracteres (31% do prompt)**. **São 518 (13%)** — meu script quebrou o prompt por `". "` e capturou frases vizinhas. **Inflei 2,4×, e a aprovação veio em cima desse número.** Corrigido, o ganho seria ~60 tokens. E encurtar prompt **não é remover código morto — é mudar comportamento**; **o banco não mede isto** (ele mede *"a fonte foi citada?"*, não *"soa Nidum?"*).

> **Se reabrirem, o instrumento não é o banco** — são duas sondas no log: *"como os ecossistemas da Nidum se relacionam para gerar regeneração?"* **tem** que sair `| triade`; *"quais são os ecossistemas da Nidum?"* **não pode**.

### 🏛️ Decisão da governança — o ChatND será o **chat único** dos colaboradores

**Tomada em 16/07/2026**, registrada para a reforma ser executada contra um alvo escrito. **O desenho:** institucional **e** assistente geral na **mesma ferramenta**.

| A pergunta é… | Vai para |
|---|---|
| **fora** do contexto Nidum | **Sonnet + web** (rota `geral`) |
| **do** contexto Nidum | **Sonnet + base**, sem web (rota `documentos`) |

> ⚠️ **Correção de percurso registrada:** esta decisão nasceu com **Haiku** na rota de fora. **O Davi recusou e foi medir** — `gpt-5-mini` errou as definições de SPE **e** SCP e construiu duas páginas em cima do erro, num tema que é **da ata de 08/07**. **Virou Sonnet.** Detalhe na sessão da noite.

> ⚠️ **O risco arquitetural, registrado antes de implementar:** a decisão põe **todo o peso numa única classificação** — *"isto é sobre a Nidum?"*. Antes, errar entre `rapido` e `diaadia` era inofensivo. No desenho novo, errar entre "fora" e "Nidum" significa **o bot responder sobre a Nidum de cabeça** — e, com a web, **buscado no Google sobre uma empresa homônima**. **E já havia prova de que essa fronteira é o ponto fraco:** o bug da Q14 obrigou a criar o guarda `_tem_marca_temporal`.
>
> **Consequência de projeto:** a binária tem que ser **enviesada — na dúvida, base.** Falso positivo = ~1 s de busca desperdiçada; falso negativo = resposta inventada sobre a Nidum. **A assimetria decide o default.** **Foi este parágrafo que virou as duas travas determinísticas da 1.31.0.**

### Fronteira do Chico (validada)

A doutrina do Chico vive **nas tools dele** (`Chico - A Fonte`, `Convergir`,
`Convergências`), **não** no `chatnd.py`. Portanto **arrancar a doutrina do pipe não o
afeta**. O **único acoplamento real** é o **roteamento**: o modelo Chico usa o `chatnd`
como *base model*, então mudar as categorias muda para qual motor as mensagens dele vão.

### Volume do Railway: 87% → 21%

Causa: **cache de modelos**, não upload. Dois rerankers baixados no mesmo dia
(`bge-reranker-v2-m3` ~2,2 GB, órfão; `bge-reranker-base` ~1,1 GB, o ativo). Caminho
provado: `Dockerfile:95` `SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"`
— e `/app/backend/data` **é o volume**. `du` depois da limpeza: **cache 3,2G · vector_db
277M · uploads 159M · lost+found 16K**. Regras novas registradas no `HIGIENE.md` da
esteira.

### 🔎 Achado novo: `STORAGE_PROVIDER=s3` **não** tira os arquivos do disco

Investigando por que existem **159M de `uploads/` locais** com o S3 ligado, o código
respondeu (`storage/provider.py`):

```python
def upload_file(self, file, filename, tags):
    """Handles uploading of the file to S3 storage."""
    contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)  # grava LOCAL
    self.s3_client.upload_file(file_path, self.bucket_name, s3_key)               # e sobe pro R2
```

**`s3` significa "disco E R2", não "R2 em vez do disco".** O `get_file` também **baixa do
R2 para o disco**. O disco é uma **cópia permanente de tudo que passa** — e cresce para
sempre. **Isto corrige o que eu havia escrito**: a conclusão de que "os uploads estão no
R2, não no disco" estava **errada**.

**O que salva o desenho:** o `delete_file` do S3 provider tem `# Always delete from local
storage` → apaga **os dois**. Ou seja, **a exclusão pela API limpa vínculo, embeddings,
banco, blob no R2 e a cópia local** — cinco coisas. **Reforça, agora com evidência nova,
que lifecycle rule no bucket é a ferramenta errada**: ela apagaria só o blob do R2 e
deixaria de pé o registro, os embeddings **e a cópia local**.

## Sessão 2026-07-16 — ChatND 1.26.0: busca por data em qualquer formato

**16/07/2026 — ChatND 1.26.0: busca por data em qualquer formato.**
Causa da Q14 isolada: **a pergunta dizia "13/07", o arquivo dizia "13072026"**.
Provado por **dois testes na 1.25.0** com a valve de enriquecimento **ON** —
*"reunião de 13/07"* **não achou** a ata; *"documento 13072026"* **achou e resumiu**.
A **única variável foi o token**. Solução: `_expandir_datas()` gera as variantes
dentro do `_buscar_sources`.

**Por que o formato quebrava a busca (em linguagem simples):** a busca por palavra
(BM25) casa **token a token** — para ela, "13/07" e "13072026" são palavras
diferentes, sem parentesco. E a busca semântica entende **assunto**, não
**calendário**: ela não sabe que "13 de julho de 2026" é a mesma coisa que "13/07".
Com as duas cegas para a data, a ata ficava de fora **por pontuação**, com vagas
sobrando — não era ruído nem falta de espaço.

**Onde a expansão mora — e por que não no `_texto_de_busca`:** ela ficou dentro do
`_buscar_sources`. O `_texto_de_busca` também alimenta a **rota de imagem** (injetaria
variantes de data em prompt de imagem) e o **gatilho do piso** dos fundadores. Assim,
**só a consulta de busca muda**; a pergunta que vai ao modelo fica intacta.

**Dependência que não pode ser esquecida:** a 1.26.0 **depende** da valve
*"Enriquecer o texto da pesquisa híbrida"* estar **ON** — é ela que põe o **nome do
arquivo** (tokenizado) no texto que o BM25 enxerga. Sem ela, o token `13072026` **não
existe em nenhum texto pesquisável** e só a variante por extenso paga. **Duas metades
da mesma ponte.** Desligar a valve regride a busca por data **sem que o sintoma aponte
para o toggle**.

**Também confirmado:** a valve age **em tempo de consulta** — **não exige reindexar**.
Os mesmos trechos subiram de 0,669/0,409/0,242/0,213 (OFF) para 0,847/0,528/0,426/0,344
(ON), sem tocar na base.

**Dívida anotada:** o índice BM25 é **reconstruído do zero, com a coleção inteira, a
cada pergunta** (`BM25Retriever.from_texts`, `retrieval/utils.py:382`). **Irrelevante
com 86 documentos** — é parte dos ~7s atuais —, mas **escala com o tamanho da base**.
Quando ela crescer, **o gargalo será esse, não o reranker**. Não foi tratado.

**Também nesta sessão (1.24.0 e 1.25.0, no mesmo republish):**
- **1.24.0** — `MAX_DOCS_INTEIROS=0` passa a **desligar de verdade**: o bump por pedido
  fundacional religava a injeção de documento inteiro por baixo (3 documentos, 159.849
  de 200.000 caracteres) **enquanto o log dizia "desligado"**. O log passou a reportar
  **o que aconteceu**, nunca a valve — foi ele que escondeu o bug por uma rodada.
- **1.25.0** — a **etiqueta** passa a refletir **o que foi citado**, não o que entrou no
  contexto (o contexto não discrimina: a Fonte entrava em toda pergunta). Formato virou
  **lista fechada** — `[Fonte] | [Acervos] | [Fonte + Acervos] | [Fora do acervo]` —
  corrigindo a etiqueta malformada `[Acervos . <caminho de pasta>]`, que era **ensinada**
  por uma instrução da v1.18.0 (refletir a pasta na etiqueta), agora **removida**.

### Resultado medido — banco de perguntas na 1.26.0 com `r=0`: **18 OK / 1 PARCIAL / 0 FALHOU**

Subiu de **14 OK/18** (rodada 1.23.0) para **18 OK/19**, **zero FALHOU**. Config:
`Top K=24 · Reclass.=24 · r=0 · híbrida ON · enriquecimento ON · bge-reranker-base ·
BM25 0,5 · BASE=ACERVOS+FONTE · MAX_DOCS_INTEIROS=0 · TOP_K_DOCUMENTOS=0`, wrapper
`chatnd`, **usuário comum** (não-admin — importante: admin pula a checagem de acesso).

**A Q14 fechou, e o diagnóstico final não era o que eu supunha.** A expansão de datas
(1.26.0) era **necessária mas não suficiente**: ela põe a ata no **pool de candidatos**
(via BM25), mas quem decide o score final é o **reranker** — um modelo **semântico**,
**surdo ao token `13072026`** — e o `RELEVANCE_THRESHOLD` cortava o chunk da ata antes
de ele aparecer em qualquer log. Numa pergunta **longa e mista**, o reranker pontuava a
ata **abaixo de 0,1**; numa pergunta **curta e sobre o documento** ("resuma o documento
13072026"), pontuava alto. **Com `r=0` a ata sobrevive e a Q14 vira OK.**

> **Decisão: `r=0` fica.** O placar subiu e o ruído de score baixo **não fez dano** — o
> modelo ignora trecho irrelevante e cita o que presta. **Registro do meu erro:** eu
> havia recomendado um piso de 0,2–0,3; teria sido **pior que inútil** — descartaria a
> própria ata, que pontua **0,244/0,266**. Quem evitou isso foi a **medição**.

**As etiquetas se consertaram:** as 3 PARCIAL da rodada anterior (P5 malformada com
caminho de pasta, P8 e P15 rotulando `[Fonte]` para conteúdo dos Acervos) vieram
limpas. A regra de **etiqueta por citação** e o **formato fechado** (1.25.0) pegaram.

**Sobrou 1 PARCIAL:**
- **P10** — etiqueta residual: rotulou `[Fonte]` mas cita **também** a Convergência CVI
  (Acervos) no fecho; deveria ser `[Fonte + Acervos]`. A regra manda contar **tudo** que
  foi citado; ele contou só a citação principal.

**A P8 era suspeita de regressão e NÃO é — virou OK.** Uma rodada respondeu que "o
documento foi cortado antes dessa seção" e ofereceu a CVI de 23/06. **Re-testada duas
vezes, acertou nas duas:** *sem data* → `[Fonte + Acervos]` com o **mapa das três
convergências** (21/05, 08/06, 23/06) e as questões de cada uma; *com data* →
`[Acervos]` com **as quatro questões em aberto** do CVI 08/06, como na linha de base.
**Foi variação de rodada, não padrão.**

> **Hipótese investigada e DESCARTADA por teste — não reabrir:** *"a expansão de datas
> (1.26.0) envenena o reranker"*. O raciocínio era plausível: a query expandida fica com
> metade do texto em variantes de data, o reranker é um cross-encoder **semântico** e vê
> a query inteira, então os chunks com a **data** (o cabeçalho) superariam o chunk com o
> **conteúdo** (as quatro questões, no fim do documento) — o que casaria com o sintoma
> *"cortado antes dessa seção"*. **O teste matou a hipótese:** a pergunta **com data** foi
> a **mais precisa** das duas; se houvesse poluição, seria a **pior**.
> **Consequência: multi-query NÃO implementado.** Era o plano B combinado
> (`queries=[original, expandida]`, merge pelo maior score por chunk), mas custa **~2×
> latência** e o gatilho — regressão comprovada — **não existe**. Só reabrir com **padrão
> reproduzível**.

**Lição de método (a mais cara desta rodada):** uma rodada não é evidência. Eu teorizei
sobre a causa de uma falha que **não se reproduzia** — e a teoria era boa o bastante para
custar 2× de latência em produção. O banco existe justamente para separar **padrão** de
**ruído**, e só faz isso se a gente **re-testar antes de teorizar**. Duas perguntas ao
ChatND custaram um minuto e pouparam uma mudança de arquitetura.

### Pendências anotadas (sem urgência)
1. ~~**A valve `FUNDADORES_SEMPRE` tem nome enganoso desde a 1.21.0.**~~ ✅ **RESOLVIDA na
   1.28.0** — virou duas valves honestas (ver abaixo).
2. ~~**O piso injeta 120k mesmo com `pri` legítimo.**~~ ✅ **RESOLVIDA na 1.28.0** — o ramo
   do gatilho nasce **desligado** (ver abaixo).
3. **O `chatnd` não mostra Origens ao usuário.** Lacuna de **auditabilidade** para um bot
   institucional: a resposta cita o documento no texto, mas o usuário não vê a lista de
   fontes recuperadas (o wrapper `Nidum 1.0 - Documentos` mostra). Sem poder conferir a
   origem, a etiqueta vira promessa em vez de prova.

### 1.28.0 — o piso dos Fundadores, e a medição que fechou o caso

A governança reordenou a prioridade: **as perguntas dos coautores são cada vez mais sobre
o operacional do SharePoint e cada vez menos sobre os fundadores. A Fonte é âncora, não
protagonista.** Isso mudou o peso da dívida do piso — e a medição mostrou que a dívida era
maior do que a gente supunha.

**A prova, medida em produção antes do deploy.** Pergunta: *"A decisão de 13/07 está
alinhada com o combinado?"* — **100% operacional**, sobre uma ata:

```
trechos:20 chunk(s)/42589 chars | inteiros:desligado | fundadores:120000 chars (piso ON) | usado:162589/200000
```

**120.000 chars de v29+v30 injetados numa pergunta sobre ata, só porque a palavra
"alinhada" contém `alinhad`.** E o dado decisivo: nessa mesma busca, os chunks da FONTE
pontuaram **0,0048 / 0,0034 / 0,00028**. Ou seja: **o reranker já tinha dito, com todas as
letras, que a Fonte não tinha nada a ver com a pergunta — e o piso passou por cima.** Não
é só "gatilho frouxo": é o piso **anulando o julgamento do rankeador** que passamos dois
dias afinando. O abafamento que a 1.21.0/1.23.0 eliminaram estava voltando **pela porta
dos fundamentos**.

**"Depois" esperado** (conferir no log após publicar): `fundadores:0 chars (piso off)` e
`usado ~42k/200000`.

**O conserto:** uma valve que fazia duas coisas vira **duas valves honestas** —
`FUNDADORES_INTEIROS_SE_GATILHO` (**default False**, aposenta os 120k por gatilho) e
`ANCORA_FUNDADORES_SE_BUSCA_VAZIA` (**default True**, preserva a rede de segurança de
quando a busca volta vazia). São coisas sem relação: uma é **escolha de política**, a
outra é **sintoma de recuperação falha**. O log passa a nomear o ramo
(`piso gatilho|busca-vazia|off`) — **`busca-vazia` recorrente é alarme**, e o `ON` antigo
escondia isso atrás de uma palavra só.

> **Política registrada (governança):** o fundador deve ser **achado pela busca** quando a
> pergunta remete à Fonte — **não injetado à força** por substring. Evidência de que
> funciona: P9–P13 (as 5 fundadoras do banco) dão **OK**, com o v30 entrando por
> **relevância**.

**O que NÃO foi construído, de propósito:** a "segunda busca restrita à FONTE" que
garantiria fundadores nos trechos. Sem evidência de que precisa. *(Lição da P8, aplicada
no mesmo dia: não fabricar máquina contra problema não comprovado. Se o banco regredir com
o gatilho off, aí se constrói — com evidência.)*

**Correção de rota registrada:** a proposta inicial era *"o `pri` empurra os fundadores no
ranking em vez de anexar inteiros"*. Isso seria **no-op**: o `pri` reordena `ordem`, que
alimenta `escolhidos` (documentos **inteiros**) — lista **morta** desde a 1.24.0
(`MAX_DOCS_INTEIROS=0`). Os **trechos** vêm de `sources` (a busca), que o `pri` **não
toca**. Comentário do código corrigido junto: ele ainda descrevia o comportamento da
v1.12.0.

⚠️ **Migração de valve persistida (fazer no painel, não tem automático):** valve é salva
no banco e o default do código **só vale na primeira carga**. O valor antigo de
`FUNDADORES_SEMPRE` fica **órfão e é ignorado em silêncio**. Se alguém o tivesse em
`False`, a âncora **religaria sozinha**. **Antes** de publicar, anote o valor atual;
**depois**, confira `GATILHO=off` / `ANCORA=on` e **salve de propósito**.

---

## Sessão 2026-07-10 — Versionamento do código e das docs no Git (fonte da verdade)

**Regra permanente adotada:** o **Git é a fonte da verdade do código**. A plataforma
(Open WebUI/Postgres) é apenas **destino de deploy**. Fica **proibido editar funções
direto na plataforma** sem que a mudança exista antes no repositório. Este arquivo
(`_nidum_docs/07_Diario_e_Status.md`) passa a ser o **diário oficial** do projeto —
toda decisão/mudança de status é registrada primeiro aqui.

**Item B — `chore/versionar-fonte-das-funcoes` (código das funções no Git):**
- Os **4 objetos** do ChatND foram versionados em `_nidum_tools/` (nome do arquivo =
  id do objeto). `chatnd_router.py` renomeado para `chatnd.py` (é o **pipe**, não o
  roteador). `__pycache__`/`*.pyc` fora do Git (**Item E**).
- **B.3 satisfeito — confirmado pelo Davi:** os 4 arquivos foram **exportados da
  plataforma VIVA hoje (2026-07-10)**, logo **disco = produção**. Versões conferidas:

  | Objeto | version (= produção) |
  |---|---|
  | `chatnd.py` (pipe) | 1.17.0 |
  | `gerador_de_arquivos_nidum.py` | 2.2.0 |
  | `nidum_fonte_quadro_de_pessoas.py` | 0.6.0 |
  | `roteador_semantico_da_fonte_nidum.py` | 0.2.0 |

**Item C+D — `chore/versionar-docs-e-runbooks` (esta entrada):**
- `_nidum_docs/` (documentação) e `_nidum_manutencao/` (runbooks) versionados no Git
  (add cirúrgico — sem `git add -A`).
- `backup/` adicionado ao `.gitignore`: são **retratos locais** do código das funções
  (podem conter segredos em valves) — não vão ao Git; o código oficial vive em
  `_nidum_tools/`.
- **C+D.2 — RESOLVIDO (opção b):** decidido que **não** há registro único. Este
  diário é o oficial da **plataforma**; a **esteira** mantém o seu em
  `nidum-chatnd-basefonte/_docs/REGISTRO_TRABALHO.md`. São dois registros distintos
  de propósito — **nenhum vira ponteiro do outro**. Registrada a nota de referência
  cruzada no topo deste arquivo. (Não existe REGISTRO no `nidum-platform` a converter.)

**Item A — CONCLUÍDO (branch `feat/fontes-da-marca-no-build`):** fontes da marca no build.
- **Dockerfile reconstruído do zero** (a modificação anterior, não-commitada, foi perdida
  quando um `git reset --hard` da branch de docs a descartou — lição: nunca mais
  `reset --hard`, usar `checkout -b <branch> origin/main`). Reconstrução conforme spec:
  `fontconfig` no `apt`; instala os 8 `.ttf` em `/usr/share/fonts/nidum` + `fc-cache`;
  **sem guarda silencioso** — se `./open_webui/static/brand/fonts` não existir, imprime
  **`AVISO: fontes da marca ausentes — PDFs sairão com fonte de fallback`** (avisa, **não
  falha**, para não quebrar clones sem os assets).
- Commit único com `Dockerfile` + `static/brand/` (8 `.ttf` + 5 logos). Redistribuição
  **autorizada verbalmente** pela empresa de branding; **confirmação por e-mail a caminho**.
- **TESTE 1 (build local):** exit 0; o passo das fontes imprimiu `OK: fontes da marca
  Nidum instaladas em /usr/share/fonts/nidum` (achou os assets, não caiu no AVISO).
- **TESTE 2 (`fc-list` no container):** as **8 fontes** aparecem no fontconfig
  (`Ibrand` + 7 pesos de `Maxima Nouva`).
- **TESTE 3 (alternativa aprovada — reportlab em container efêmero):** replicado o caminho
  real da ferramenta (`_font_path` + `registerFont`); `pdffonts` do PDF gerado prova
  **embedding**: `AAAAAA+MaximaNouva-Regular`, `AAAAAA+MaximaNouva-Bold`,
  `AAAAAA+Ibrand-Regular` — todos `emb=yes sub=yes`, carregados de
  `/app/backend/open_webui/static/brand/fonts`.

**Dois achados (Item A) para quem mantém:**
1. **O PDF da ferramenta NÃO usa o fontconfig.** O motor é **reportlab**, que carrega os
   `.ttf` **por caminho** (`os.path.dirname(open_webui.__file__)/static/brand/fonts`).
   Quem garante isso na imagem é o `COPY ./backend .` (assets agora versionados). O
   `fontconfig`/`fc-cache` do Dockerfile serve os caminhos **HTML/`@font-face`**, não o
   PDF do reportlab — mas ambos ficam cobertos.
2. **`reportlab` não está na imagem base** (`ModuleNotFoundError` no container). É
   **esperado**: o Open WebUI instala os `requirements:` da ferramenta
   (`python-pptx, openpyxl, python-docx, reportlab`) **em tempo de carregamento da tool**,
   não no build. Por isso o teste do reportlab exigiu `pip install` no container.

**PENDENTE (Item A):** **conferência visual "de olho" na UI** — só um humano fecha, num
Open WebUI rodando, gerando um arquivo pela ferramenta e olhando a tipografia. Fica para
pós-merge. *(Obs.: o build emitiu 2 warnings pré-existentes — `OPENAI_API_KEY`/
`WEBUI_SECRET_KEY` como ENV na linha 80 do Dockerfile; não é desta mudança.)*

**Ordem de execução aprovada:** **B → C+D → E → A**. O Item A só é mergeado **depois**
de B e C+D.

## Sessão 2026-07-02 — ChatND v1.17.0 (Fase C: imagem conversacional) — EM VALIDAÇÃO

- **Pipe ChatND → v1.17.0 (em produção, Fase C EM VALIDAÇÃO):** imagem conversacional/multi-turno. **C1 (roteamento ciente de contexto):** ajuste/crítica de uma imagem recém-gerada passa a rotear como *imagem* (antes virava texto). Âncora determinística `_ultima_foi_imagem` pelo marcador EXATO (`_MARCADOR_IMAGEM`, constante compartilhada por âncora+parser+saída). Trava anti-falso-positivo: conversa comum pós-imagem ("valeu, qual o prazo?") continua indo para texto. **C2 (contexto no caminho de imagem):** `_gerar_imagem` recebe o contexto recente do usuário (tema persiste entre turnos) + a descrição da imagem anterior (da mensagem crua, degradação segura); numa revisão, mantém a base e soma o ajuste (comando dominante), reusando a fusão da Fase B.
- **Validação C3 (por API):** roteamento (ajuste→imagem; conversa→texto); revisão sob tensão = base preservada (tucunaré/bandeira/degradê) + tema correto (despedida DE SOLTEIRO: taças, gravata, "DESPEDIDA DO NOIVO" — não gaivotas/adeus) + presença sólida (não translúcida), tudo junto; ajuste pequeno ("gola vermelha") proporcional, sem inflar; tema entre turnos; fusão; não-regressões. `py_compile` OK, ASCII. Backup do v1.16.0 em `backup/02-07-2026/chatnd_LIVE_v1_16_0_antes.py`. Pós-publish: versão ativa 1.17.0, live byte-idêntico, valve `BASE_CONHECIMENTO_ID=60dfba25` intacta.
- **DECISÕES DE DESIGN (registradas para NÃO serem "consertadas"):** (i) **revisão por TEXTO** (descrição anterior), não por imagem/URL — fidelidade iterativa e menor risco (URL comporia erro sobre erro e expira com a retenção); revisão por imagem fica com a **opção (b) image-to-image, condicionada**. (ii) O **equilíbrio da instrução de revisão** (base preservada × ajuste com presença real) foi calibrado de propósito, com a frase de fecho da integração — **mexer reabre o risco de oscilar** para um extremo (ajuste sutil demais / ajuste que engole a base).
- **⚠️ PENDÊNCIA BLOQUEANTE-DE-FECHAMENTO (Fase C) — 2º smoke test humano na interface.** Publicar 1.17.0 é **"em validação"**, não "concluída". O comportamental está provado por API; o fluxo real da interface só um humano fecha.
  - **Executor: a definir pelo Davi** (exige acesso à UI — Davi ou os dois Thiagos; não dá via API).
  - **Roteiro:** (1) gerar uma imagem, depois pedir um **ajuste** ("adicione X", "muda a cor") → deve vir a **imagem REVISADA** (não texto), preservando a base e somando o ajuste; (2) **tema num turno + anexo no seguinte** ("tema despedida de solteiro" → "use o anexo") → imagem com o tema **e** a referência juntos. Se o ajuste vier como texto (roteou errado) ou a revisão perder a base/tema, reportar para recalibrar.

### 🗺️ MAPA CONSOLIDADO desta linha de trabalho (imagem) — para quem retomar

- **5 bugs, todos tratados no CÓDIGO e no ar:**
  1. Identidade visual vazando em imagem (v1.15.0 — branding neutro por padrão).
  2. Guarda de anexo / imagem gerada sem descrição (v1.15.1 — guarda estrutural + sentinel).
  3. Imagem-lixo (v1.15.1 — consequência do #2, resolvida junto).
  4. Anexo descartado / sem uso como referência (v1.16.0 — refino assistido por visão).
  5. Multi-turno: roteamento de ajuste (C1) + contexto entre turnos (C2) (v1.17.0).
- **O que RESTA (não é código):**
  - **2 smoke tests humanos pendentes:** Fase B (anexo real → imagem que reflete a referência) e Fase C (gerar → ajustar → ver imagem revisada; tema+anexo entre turnos). Ambos exigem a interface; executor a definir com o Davi. **Bloqueiam o "concluída" de cada fase, não o uso.**
  - **Opção (b) image-to-image:** MAPEADA e ADORMECIDA. Só reabrir se a revisão/fusão por texto se mostrar insuficiente **E** após verificar o mismatch `IMAGE_EDIT_ENGINE=openai` × `IMAGE_EDIT_MODEL=imagen-3.0-generate-002`. Não é trabalho fantasma.

---

## Sessão 2026-07-02 — ChatND v1.16.0 (Fase B: imagem de referência) — EM VALIDAÇÃO

- **Pipe ChatND → v1.16.0 (em produção, mas Fase B EM VALIDAÇÃO, não concluída):** corrige o **Bug 1** (anexo de imagem era descartado) via **refino assistido por visão** (opção a). Havendo anexo, a imagem vai como referência ao refino multimodal (modelo de refino é multimodal — confirmado); a engine segue texto-para-imagem. A **ponte da Fase A** deixou de ser o comportamento padrão e virou **salvaguarda de erro** (anexo detectado mas não-extraível → mensagem honesta, sem imagem-lixo). Cláusula nova no `IMAGEM_PROMPT`: combinar referência + texto e **não reproduzir marcas/logotipos/emblemas/patches de terceiros** (princípio: não trazer identidade visual de terceiros para a nova peça). Branding neutro (v1.15.0) + sentinel (v1.15.1) intactos sem anexo.
- **Validação por API (5 testes):** (1) fusão sob tensão → herda forma+cores da referência E troca o tema (peixe→despedida de solteiro), substituindo o emblema por elemento do tema (anel) — **decisivo, passou**; (2) controle de logo → marca de terceiro removida; (3) anexo não-extraível → mensagem honesta; (4) texto neutro → sem regressão; (5) marca explícita → paleta incorporada. `py_compile` OK, ASCII. Backup do v1.15.1 em `backup/02-07-2026/chatnd_LIVE_v1_15_1_antes.py`. Pós-publish: versão ativa 1.16.0, live byte-idêntico, valve `BASE_CONHECIMENTO_ID=60dfba25` intacta.
- **DECISÃO DE DESIGN (registrada para NÃO ser "consertada"):** no caso **neutro** (sem tema novo) pode restar um **bordado genérico** no lugar do logo — **ACEITO por decisão**. Forçar "superfície lisa" foi avaliado e **rejeitado**: arriscaria o caso de uso real (fusão com tema), que aprendeu a *substituir* o emblema por elemento do tema em vez de apagar. O resíduo neutro **não é branding alheio** (a marca é removida ativamente). Se um dia incomodar, o caminho é a **opção (b) image-to-image** com controle de fidelidade — **não** endurecer esta cláusula.
- **(b) image-to-image = possibilidade mapeada, ainda condicionada** — só reabrir se (a) se mostrar insuficiente **E** após verificar o mismatch `IMAGE_EDIT_ENGINE=openai` × `IMAGE_EDIT_MODEL=imagen-3.0-generate-002`. Não é trabalho fantasma.
- **⚠️ PENDÊNCIA BLOQUEANTE-DE-FECHAMENTO (sobrevive à troca de sessão): 2º smoke test humano — anexo real na interface → imagem que reflete a referência (fusão), sem branding de terceiros.** Publicar 1.16.0 é **"Fase B em validação"**, não "Fase B concluída" — o refino multimodal foi provado por API, mas o fluxo end-to-end da interface (anexo real → imagem final) só se prova com upload humano.
  - **Executor: a definir pelo Davi** (quem e quando); exige acesso à interface (Davi ou os dois Thiagos), não dá via API.
  - **Roteiro:** (1) anexar uma **camisa real** e pedir um **tema novo** ("faca uma camisa como esta, mas com tema X") → a imagem gerada deve **refletir a forma/estilo da referência com o tema pedido** (fusão), **sem** reproduzir logos/emblemas de terceiros; (2) anexo que **não é imagem** (ex.: PDF) → **sem** imagem-lixo (mensagem honesta ou sentinel). Se a fusão não acontecer (imagem ignora a referência, ou copia a peça literal), reportar para recalibrar a cláusula ou reconsiderar a opção (b).

---

## Sessão 2026-07-02 — Smoke test de anexo PASSOU; Fase B desbloqueada

- **RESOLVIDA a pendência "validar detector de anexo com upload real end-to-end".** Evidência: em produção, um anexo de imagem **real** enviado pela interface (pedido "utilize a imagem em anexo de modelo") disparou a **mensagem-ponte honesta**, **sem imagem-lixo**. Confirma que `_tem_anexo_imagem` pega o formato de anexo real **desta instância** — o risco de falso-negativo que bloqueava a Fase B **não se materializou**. O passo 2 do roteiro (texto puro, sem anexo, gera normalmente) ficou coberto pelo mesmo uso.
- **DESBLOQUEADO:** a dependência *"Fase B (B0) bloqueada até o smoke test passar"* está **LIBERADA** (referência: evidência acima). A Fase B pode começar pelo **B0 (diagnóstico)**.
- **Passo 3 do roteiro (anexo que NÃO é imagem, ex.: PDF)** fica como **verificação de robustez a fazer durante a Fase B** — é lá que o tratamento de tipos de anexo será reescrito de qualquer forma; **não é bloqueante** para iniciar o B0.
- *(A pendência original e o roteiro completo dos 3 passos seguem preservados abaixo, na entrada da v1.15.1, como registro do que foi verificado.)*
- **B0 (diagnóstico) concluído — arquitetura escolhida: (a) refino assistido por visão.** Confirmado empiricamente que o modelo de refino (gpt-5-mini) é **multimodal** (leu corretamente uma imagem-teste). O anexo será passado ao refino, que "vê" a referência e a incorpora na descrição; a engine segue texto-para-imagem (`gemini`/`imagen-4.0`). Menor raio, funciona hoje, sem tocar em engine/config/deploy; fidelidade média cobre "parecida/como modelo".
- **(b) image-to-image via `image_edits` = POSSIBILIDADE MAPEADA, NÃO pendência ativa.** O backend tem caminho de edição nativo (`EditImageForm(image=..., prompt=...)`), mas fica **condicionado** a: (1) a opção (a) se mostrar insuficiente na prática **E** (2) verificar o mismatch de config `IMAGE_EDIT_ENGINE=openai` × `IMAGE_EDIT_MODEL=imagen-3.0-generate-002`. **Não é trabalho fantasma** — só reabrir se (a) não bastar.

---

## Sessão 2026-07-02 — ChatND v1.15.1 (hotfix do caminho de imagem, Fase A)

- **Pipe ChatND → v1.15.1 (em produção):** hotfix dos 3 bugs do caminho de imagem. **Bug 2** (gerava imagem sem descrição válida) e **Bug 3** (imagem-lixo, que era consequência do Bug 2) **resolvidos** por: (a) **guarda estrutural de anexo** (`_tem_anexo_imagem` pelo `type` declarado das partes; `_gerar_imagem` recebe `tem_anexo_imagem`) → curto-circuito honesto sem chamar o motor; (b) **sentinel `SEM_IMAGEM:`** no `IMAGEM_PROMPT` + guarda no pipe → pedido não-imagem/dependente de anexo vira mensagem normal, sem gerar. As duas guardas são independentes (anexo antes do refino; sentinel depois).
- **Bug 1 (anexo descartado) segue aberto DE PROPÓSITO:** a guarda de anexo é uma **ponte intencional e temporária** (`# PONTE FASE A - substituir na Fase B`). O suporte real a imagem de referência (multimodal) é a **Fase B → v1.16.0**. **Não "consertar" a ponte** achando que é esquecimento — é trabalho já sequenciado.
- **Validação (4 testes comportamentais):** (1) café realista → gera neutro; (2a) "capital da Franca?" → `SEM_IMAGEM:`, não gera; (2b, fronteira) "faca igual a camisa que te mandei" sem anexo → `SEM_IMAGEM:`, não gera (falha da imagem-lixo pela via textual, capturada); (3) anexo `image_url`/`files` → detector=True, ponte honesta; (4) "banner com as cores da Nidum" → paleta incorporada (sem regressão da v1.15.0). `py_compile` OK, ASCII. Backup do v1.15.0 em `backup/02-07-2026/chatnd_LIVE_v1_15_0_antes.py` (rollback possível). Verificado pós-publish: versão ativa 1.15.1, live byte-idêntico, valve `BASE_CONHECIMENTO_ID=60dfba25` intacta.
- **⚠️ PENDÊNCIA (sobrevive à troca de sessão): validar detector de anexo com upload real end-to-end (smoke test).** A cobertura por código (misc.py: `image_url` + `input_image` na lista) e o teste simulado provam que o detector funciona; falta confirmar o **embrulho exato** do fluxo frontend→backend nesta instância (parte em `content` vs `files` no nível da mensagem) com um **anexo de imagem real** enviado pela interface. Se der falso-negativo, contingência barata: acrescentar a chave observada à lista de `_tem_anexo_imagem` (1 linha) e republicar.
  - **BLOQUEANTE — Fase B (B0) bloqueada até o smoke test de anexo real passar.** A Fase B remove a ponte que hoje contém o caso de anexo; se o detector tiver falso-negativo nesta instância, descobrir isso *depois* de remover a ponte trocaria um bug conhecido e contido por um bug silencioso. Ordem obrigatória: **smoke test passa → só então B0.** (Não é dependência técnica de escrita da Fase B; é dependência de segurança da sequência.)
  - **Executor: a definir pelo Davi** (quem e quando). Exige acesso à interface — só o Davi ou os dois Thiagos; não dá para fazer via API.
  - **Roteiro mínimo (para ser conclusivo, não só "abri e pareceu ok"):** (1) anexar uma imagem **real** a um pedido de imagem ("faca uma camisa parecida com esta") → deve aparecer a **mensagem-ponte honesta**, NÃO imagem-lixo (prova que o detector pega o anexo real desta instância); (2) pedido de imagem por **texto puro, sem anexo** → deve **gerar normalmente** (prova que não há falso-positivo bloqueando o fluxo normal); (3) pedido de imagem com anexo que **NÃO é imagem** (ex.: PDF) → **não** deve gerar lixo.
  - **Se o passo (1) falhar** (imagem-lixo em vez da ponte) = o falso-negativo previsto: correção de **1 linha** (acrescentar a chave observada à lista de `_tem_anexo_imagem`) + republicar; quem executar deve **anotar o formato exato do anexo** que apareceu, para essa correção.

---

## Sessão 2026-07-02 — ChatND v1.15.0 (imagem sem branding por padrão)

- **Pipe ChatND → v1.15.0 (em produção):** Abordagem 5 (co-localização de instruções). Mudou **só** a constante `IMAGEM_PROMPT`: o default de geração de imagem deixou de aplicar a identidade visual da Nidum e passou a **fotorrealista neutro**; a paleta (terracota/verde/azul/creme) ficou **preservada** na constante, mas só entra quando o usuário pede a marca explicitamente. Corrige o "vazamento de instrução" que deixava fotos realistas artificiais. Bloco de refino e contrato de saída **intactos**; wrappers e tool **não** tocados.
- **Validação comportamental** (descrições refinadas do motor de refino): (a) "café realista numa mesa de madeira" → descrição neutra, sem hex/logo/estética corporativa; (b) "banner com as cores da Nidum" → paleta completa (4 hex) incorporada. `py_compile` OK. Publicado **só o pipe** via API. Backup do v1.14.0 em `backup/02-07-2026/chatnd_LIVE_v1_14_antes.py` (rollback possível).
- **Contexto do mesmo dia (sessões anteriores):** v1.14.0 (classificador por princípio — perguntas institucionais curtas vão para *documentos*), v1.13.0 (fusão etiqueta `[Fonte]` + piso dos fundadores), tool v2.2.0 (geração não-bloqueante + traceback só no log + tolerância a R2); migração de infra concluída (Postgres + pgvector + R2); verificações pós-deploy (workers=1; fallback de tags do R2 não dispara; logger `gerador_nidum` comprovadamente visível nos logs); follow-up do chat reduzido para 2 sugestões.

---

## Estado atual (2026-07-16)

### ✅ Pronto e em produção
- **Busca por data:** **resolvida na 1.26.0** — a pergunta acha o documento em qualquer
  formato de data (por extenso, barras, pontos, hífens, compacto, ISO, abreviado).
  **⚠️ Dependente da valve *"Enriquecer o texto da pesquisa híbrida"* estar ON.**
- **Plataforma base:** Open WebUI 0.9.6 (fork) no Railway, domínio `chatnd.nidumbrasil.com.br`, com SSL. Login com aprovação manual.
- **ChatND (roteador) v1.10.0:** classificação + 6 rotas; RAG modo documento-inteiro; geração de arquivos e imagens; voz da tríade.
- **Ferramenta de arquivos v2.1.0:** PPTX/PDF/DOCX/XLSX/HTML/Deck on-brand (paleta + Maxima Nouva + Ibrand + logos).
- **RAG:** base `a85d8a8f` (MVP - Agente Chico); priorização dos documentos fundadores (v29/v30) corrigida.
- **Voz Nidum:** tríade fonte/forma/fluxo (rotas documentos/raciocínio/arquivo, só quando aplicável); etiquetas de certeza; nunca revela o LLM.
- **Geração de imagem:** Gemini (`imagen-4.0-generate-001`), como recurso.
- **Editorial (backend):** ingestão `.docx/.pdf/.epub/.odt` + export `.docx/.epub/.pdf` + ficha (F3 núcleo), em produção via API.
- **Branding:** wordmark "nidum"; nome "Nidum AI" sem sufixo "(Open WebUI)".

### 🔧 Em andamento / parcial
- **Editorial F3 (ficha no chat):** núcleo pronto; falta o vínculo "modelo por projeto" (manifold no seletor) — peça de deploy.
- **Editorial F2.4b:** embutir imagens nos exports (docx/epub/pdf) com alt-text — planejado.
- **Imagem no fluxo do ChatND:** funciona como recurso; integração total ao fluxo conversacional em refinamento.

### ⛔ Bloqueado / risco operacional
- **Volume do Railway cheio (incidente 2026-06-30):** a geração de arquivo chegou a falhar com "No space left on device". Liberados ~35 MB (dedup do Deck Documento Fundador + imagens antigas); geração voltou. **Mas o volume é só 500 MB e inclui Chroma + banco — vai apertar de novo.**
- **OOM em upload/indexação:** subir PDFs grandes pela base causa pico de RAM e crash. Resolução durável = mais memória (depende de billing).
- **Billing do Railway baixo:** se o crédito acabar, o serviço é suspenso (ChatND fora do ar). Conferir no painel.

### ➡️ Próximos passos (ordem de prioridade definida pelo usuário)
1. **Separação de memória (banco em Postgres)** — tirar o estado/banco do volume local; alivia volume e OOM, e dá durabilidade.
2. **Volume / billing** — resolver crédito do Railway e dimensionamento.
3. **Grupos / permissionamento** — controle de acesso mais fino.

---

## Histórico (acrescentar no topo; não apagar)

### 2026-07-02 — MIGRAÇÃO DE ARMAZENAMENTO CONCLUÍDA (cutover)
- **Infra nova em produção:** banco em **Postgres** (Railway, serviço `Postgres-EM0i`), vetores em **pgvector** (substituiu o Chroma), arquivos em **Cloudflare R2** (bucket `nidum-arquivos`). Volume antigo (SQLite+Chroma) mantido intacto como backup.
- **Fresh start (A1) reconstruído:** admin novo (`tecnologica@nidumbrasil.com.br`), conexões OpenAI+Anthropic, 4 motores, ChatND v1.11.2 (público; motores privados), tools (gerador, quadro de pessoas), filtro semântico, imagem Gemini, code-interpreter off, RAG híbrido 2200/300.
- **Base de conhecimento nova:** "Base Institucional Nidum" (`60dfba25`, dona=admin), 28 arquivos re-embedados. `Homo Integralis` e `Empresas Vivas` entraram como `.txt` (extrator do app falhava nesses 2 PDFs).
- **Chico restaurado:** `chico-m1` (wrapper sobre o ChatND) com prompt original, tool e filtro religados, base nova; validado ("quem é quem" + "em aberto").
- **Validações:** RAG (ecossistemas pela v30) ✓ · geração de arquivo → R2 ✓ · rotas OpenAI e Claude ✓.
- **Ajuste de produção:** pool do Postgres `DATABASE_POOL_SIZE=10/OVERFLOW=20` (default estourava em uploads em série).

**Ajustes pós-cutover (02/07, mesma data):**
- ✅ **Etiqueta `[Fonte]`** em colchete restaurada — a instrução injetada na rota documentos agora manda abrir com `[Fonte - …]`/`[Convergência - …]` (roteador **v1.12.0**).
- ✅ **System prompts dos motores restaurados** — o `create` não aplicou os `params.system`; recriados a partir do `webui.db` antigo via console (rápido 3521 / dia-a-dia 3540 / documentos 6575 / raciocínio 3340 chars).
- ✅ **Modelos-base escondidos do seletor** — whitelist na conexão (100+ → 4 base) + overlays privados; **só o `chatnd` é público** ao usuário comum (motores, base e Chico privados).
- ✅ **Cadastro religado** (`ENABLE_SIGNUP=true`, `DEFAULT_USER_ROLE=pending`) — falta o registro manual de davi.vittori/amanda.bueno + aprovação.
- ✅ **Limpeza R2** — 11 uploads órfãos duplicados removidos (48 → 37 arquivos).

**Ainda pendente:**
- Registro manual dos usuários (davi.vittori, amanda.bueno) + promover davi a admin.
- Follow-up máx 2 + `PENDING_USER_OVERLAY`.
- PDFs órfãos dos 2 livros no R2 (a base usa os `.txt`) — decisão do usuário.
- **RETENÇÃO (não implementada)** — spec definida pelo usuário: chat **sem interação há 7 dias → comprimir** (economia de armazenamento); **sem interação há 90 dias → deletar o chat + os arquivos associados**. É funcionalidade de backend (código no fork + deploy + dry-run + agendador); tratar como tarefa dedicada.

### 2026-06-30
- **Documentação estruturante criada** (`_nidum_docs/`, 10 documentos).
- **Tríade fonte/forma/fluxo** implementada no roteador (v1.10.0): gate no classificador (só pedidos gerativos), valve `TRIADE_ATIVA`, bloco no GERADOR. Verificada nas 3 superfícies (documentos, raciocínio, arquivo).
- **Limpeza de volume:** removidas 2 de 3 cópias idênticas (SHA-256) do "Nidum Deck Documento Fundador.pdf" + 5 imagens antigas → ~35 MB liberados; geração de arquivo restaurada. Backups guardados.
- **Higiene de duplicados:** removidas cópias redundantes em bases órfã/Institucional (com backup); base Institucional `be78cf85` esvaziada exceto os PDFs v29/v30 (mantidos por regra). Mecanismo de higiene recorrente **desenhado** em `_nidum_manutencao/HIGIENE_DUPLICADOS.md` (não implementado).
- **Robustez da geração de arquivos** (roteador 1.8.0–1.9.0): GERADOR blindado (JSON válido, nunca vazio), retry + mensagem amigável, `_parse_json` robusto, oferta de gerar módulos um por vez.

### Antes de 2026-06-30 (resumo)
- Fases 0–7 do plano original concluídas: contas, deploy, domínio, volume, admin, 4 wrappers, ferramenta de arquivos, Code Interpreter desligado, RAG, controle de acesso.
- Frente Editorial F1–F4 (ingestão + chunking + aceite 80k) e F2.1–F2.4a (export docx/epub/pdf + alt-text) implementadas; marco deployado em produção.
- Branding visual, geração de imagem (Gemini), guardrails de segurança, identidade da marca nos arquivos gerados, correção do bug "não tenho acesso ao v30".

> Detalhe técnico de cada item está nas memórias do projeto (estado, lições técnicas, editorial) e no histórico de commits.
