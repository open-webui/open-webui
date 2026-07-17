# ChatND / Plataforma Nidum — instrucoes do projeto

Fork do Open WebUI 0.9.6 com o "motor invisivel" ChatND (pipe roteador) e a tool
de geracao de arquivos. Codigo Nidum vive em `_nidum_tools/`, docs em
`_nidum_docs/`, scripts de manutencao em `_nidum_manutencao/`.

## Documentacao continua (obrigatorio)

Este projeto mantem documentacao viva em `_nidum_docs/`:
- `_nidum_docs/Documentacao_ChatND_Nidum.html` — doc tecnica do pipe ChatND e da
  tool gerador_de_arquivos_nidum (diagnostico, mudancas por versao, infra).
- `_nidum_docs/07_Diario_e_Status.md` — status geral vivo do projeto.
- `_nidum_docs/00_LEIA-ME.md` ... `09_Dominio_Nidum.md` — o pacote estruturante.

### REGRA DA DOC (a mais importante desta secao)

**Doc que descreve PRODUCAO mergeia junto com o DEPLOY - nunca antes.**

POR QUE ISTO E REGRA E NAO CONSELHO: e a CAUSA RAIZ do apodrecimento dos _nidum_docs/.
Em 16/07/2026 o 03_Arquitetura_e_Motor.md errava TODOS os fatos estruturais - apontava
para um arquivo inexistente (chatnd_router.py), uma versao 18 numeros atras (1.10.0 vs
1.28.0), uma colecao aposentada e um modo de RAG desligado havia semanas. Ele nao nasceu
errado: APODRECEU, e ninguem notou porque nada obrigava a conferir.

A PROVA de que e estrutural e nao falta de disciplina: a doc 03 foi REESCRITA DO ZERO em
16/07 para consertar exatamente isso - e APODRECEU ANTES DE MERGEAR. Descrevia 6 rotas; a
fatia 1 fez 4, no mesmo dia. Uma doc escrita para consertar apodrecimento apodreceu em
horas.

A CAUSA - e ela estava ESCRITA AQUI, como obrigacao. A regra anterior dizia, literalmente:

    "Atualize Documentacao_ChatND_Nidum.html na MESMA sessao da alteracao."

O defeito: "alteracao" NAO e "deploy". Aqui pipe/tools vao por API, MANUALMENTE - mergear
na main NAO publica. Entao a doc atualizada "na mesma sessao da alteracao" fica CERTA
sobre algo que ainda NAO EXISTE e ERRADA sobre o que esta no ar. Ela documentava o commit;
o leitor precisa do que ESTA RODANDO.

    O PROBLEMA NAO ERA NINGUEM SEGUIR A REGRA. ERA SEGUI-LA.

Isso importa para quem for mexer aqui: nao adianta pedir "mais disciplina com as docs". A
disciplina existia e a regra era obrigatoria - e o resultado foi uma doc que errava TODOS
os fatos estruturais. Instrucao errada nao se corrige com esforco; corrige-se trocando a
instrucao.

NA PRATICA:
  - Doc de PRODUCAO (03_Arquitetura, 04_Dicionario, Documentacao_ChatND_Nidum.html):
    o PR mergeia QUANDO O PUBLISH ACONTECE, nao quando o codigo entra na main.
  - Se precisar mergear antes: aviso no TOPO dizendo QUAL versao ela descreve e que pode
    nao estar publicada. O aviso SAI no publish.
  - Carimbo "Ultima verificacao: <data>" no topo. Nao impede o apodrecimento - deixa ele
    VISIVEL, que e o que a doc antiga nao tinha.
  - Doc de DECISAO (07_Diario, 08_Decisoes): mergeia quando a decisao e tomada. Decisao
    nao espera deploy - ela E o registro de que se decidiu.
  - NA DUVIDA, pergunte: "isto fica FALSO se o publish nao acontecer?" Se sim, e doc de
    producao: espera o deploy.

---

Sempre que alterar o pipe ChatND, a tool gerador_de_arquivos_nidum, ou qualquer
configuracao de infraestrutura (env vars, storage, banco):

1. Atualize `Documentacao_ChatND_Nidum.html` na mesma sessao da alteracao - MAS
   respeitando a REGRA DA DOC acima: ela descreve producao, entao o MERGE espera o
   publish (ou leva o aviso no topo).
2. Registre na secao "Historico de alteracoes": data, componente, versao, O QUE
   mudou, POR QUE mudou e COMO VALIDAR (um teste concreto).
3. Se a mudanca criar/alterar valves ou variaveis de ambiente, atualize tambem as
   secoes 3, 4 ou 5 conforme o caso.
4. Linguagem objetiva e didatica, em portugues. Sem jargao desnecessario: o
   leitor pode nao ser tecnico.
5. NUNCA apague o historico - acrescente a nova linha no TOPO da tabela.
6. Ao subir a versao de um arquivo, atualize o numero de versao no docstring do
   arquivo E na secao 1 desta documentacao.
7. Atualize tambem `_nidum_docs/07_Diario_e_Status.md` a cada sessao relevante
   (acrescentando, nunca apagando o historico).

## REGRA DO CLASSIFICADOR: catch-all vence regra de desempate

**Ao escrever ou reescrever o prompt do CLASSIFICADOR: NUNCA defina uma categoria pelo
COMPLEMENTO de outra.** Nada de "TUDO que NAO e sobre a Nidum", "qualquer coisa que nao
seja X", "o resto". **Descreva cada categoria pelo que ELA E** - uma lista fechada do que
cai nela.

POR QUE (aprendido quebrando producao em 16/07/2026):

A REGRA DE DESEMPATE deste prompt ("na duvida entre 'geral' e 'documentos', SEMPRE
'documentos'") e a protecao mais importante que existe aqui: e ela que impede pergunta
institucional de ser respondida sem base - ou, com a web ligada, pelo Google, sobre uma
empresa homonima.

    MAS REGRA DE DESEMPATE SO FUNCIONA QUANDO HA DUVIDA.

Uma categoria definida pelo complemento de outra ("TUDO que NAO e X") NUNCA DEIXA RESTO.
Ela absorve todo caso que o juiz nao reconhece - e o juiz nao hesita, porque a definicao
ja lhe deu a resposta. A regra de desempate fica no prompt, intacta, e NUNCA E
CONSULTADA. Ela vive do resto, e o catch-all nao deixa resto.

O CASO CONCRETO: na fusao 6->4 (1.31.0), 'rapido'/'diaadia'/'raciocinio' - que eram
LISTAS FECHADAS ("saudacoes, traducoes curtas"; "conversa geral, redacao, analise comum";
"decisoes complexas, trade-offs") - viraram 'geral', aberto com "TUDO que NAO e sobre a
Nidum". A pergunta "o que significa 'fazer da casa um ninho'?" (frase LITERAL do
Documento Fundador) ia para 'documentos' na 1.26.0 e citava o v30. Na 1.31.0 foi para
'geral' e respondeu de cabeca, sem fonte. O gpt-5-mini nao sabe que a frase e da Nidum -
logo ela e "tudo que nao e sobre a Nidum", e a definicao mandava.

Antes: a frase nao casava com NENHUMA lista -> ficava sem caixa -> o desempate acordava.
Depois: a frase TINHA caixa -> nenhuma duvida -> o desempate nunca rodou.

O TESTE PARA QUEM FOR ESCREVER: leia a definicao de cada categoria e pergunte "existe
pergunta que nao casa com nenhuma?". Se a resposta for NAO, a regra de desempate esta
morta e voce nao vai perceber - o prompt continua bonito, o sintoma aparece semanas
depois, numa pergunta real, e parece "o modelo errou".

## Regras invioaveis do codigo

- `_nidum_tools/*.py` (pipe e tool): APENAS ASCII (sem bullets unicode, travessoes
  ou emojis). Validar com `python -m py_compile`.
- Nunca revelar qual LLM/provedor esta por tras.
- Nunca expor chaves/segredos no chat, log ou commit.
- Pipe/tool sao publicados via API do Open WebUI (`/api/v1/functions/id/chatnd/update`
  e `/api/v1/tools/id/gerador_de_arquivos_nidum/update`), nao por deploy de repo.
  Ao atualizar SO a tool, republicar tambem o pipe (reseta o cache da tool).
- Backend (editorial, branding, Dockerfile) vai por git push -> Railway (downtime).
