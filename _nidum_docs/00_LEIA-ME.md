# 00 — LEIA-ME (porta de entrada)

> **Para quem é:** qualquer pessoa que chega a este projeto pela primeira vez — da equipe da Nidum a um novo desenvolvedor ou a outro agente de IA.
> **Quando consultar:** sempre primeiro. Este documento explica o que é o projeto e aponta para onde ir em seguida.

---

## O que é o ChatND (em 3 parágrafos)

O **ChatND** é a plataforma de inteligência artificial interna da **Nidum**. Por baixo, ela é uma instalação própria (self-hosted) de um software de código aberto chamado **Open WebUI** — uma interface de chat com IA parecida com o ChatGPT, mas que roda nos servidores da Nidum, conectada às IAs da OpenAI e da Anthropic. A Nidum fez um **fork** (uma cópia própria) desse software para poder personalizá-lo livremente. O endereço em produção é **chatnd.nidumbrasil.com.br**.

O coração da plataforma é o **ChatND** propriamente dito: um "motor invisível" que recebe cada pedido do usuário, **descobre sozinho** que tipo de pedido é (uma pergunta rápida, uma análise sobre documentos da Nidum, a geração de um arquivo, uma imagem...) e **encaminha para o melhor especialista** internamente — sem o usuário precisar escolher nada. Ele também busca conteúdo na base de conhecimento da Nidum (os documentos fundadores e livros) para responder com base na fonte real, e gera arquivos (apresentações, PDFs, planilhas) já com a identidade visual da marca.

Há ainda uma segunda frente em construção dentro do mesmo projeto: a **frente Editorial** — um conjunto de funcionalidades para **ler obras** (livros em .docx/.pdf/.epub/.odt), preservar sua estrutura, e **exportá-las** em formatos editoriais (.docx/.epub/.pdf paginado), além de manter uma "ficha viva" por autor. Essa frente roda no mesmo servidor, mas por enquanto é acessada por API (sem tela própria).

## Para quem serve

- **Hoje:** uso interno em testes, com abertura prevista primeiro para os **facilitadores** da Nidum.
- **Depois** (após colher feedback e melhorar): abertura para **todos os coautores internos** da Nidum.
- O sucesso é medido por **quantidade de uso** e pelo **feedback dos coautores**.

## Mapa dos documentos

| Documento | O que responde | Quando consultar |
|---|---|---|
| **00_LEIA-ME** (este) | O que é, para quem, e onde está cada coisa | Primeiro contato |
| **[01_PRD](01_PRD.md)** | Que problema resolve, para quem, o que está dentro/fora do escopo | Para entender o "porquê" do produto |
| **[02_Guia_de_Implantacao](02_Guia_de_Implantacao.md)** | Como colocar/atualizar no ar, passo a passo | Ao fazer deploy ou configurar |
| **[03_Arquitetura_e_Motor](03_Arquitetura_e_Motor.md)** | Como o sistema pensa por dentro (o "motor" ChatND) | Para entender ou alterar o funcionamento |
| **[04_Dicionario_de_Dados_e_Configuracao](04_Dicionario_de_Dados_e_Configuracao.md)** | Cada variável, parâmetro e tabela, com seu significado | Ao configurar ou debugar |
| **[05_Guia_do_Contribuidor](05_Guia_do_Contribuidor.md)** | Como trabalhar neste repo sem quebrar nada | Antes de mexer no código |
| **[06_Cenarios_de_Teste](06_Cenarios_de_Teste.md)** | Casos de teste e o que bloqueia um lançamento | Antes de liberar uma versão |
| **[07_Diario_e_Status](07_Diario_e_Status.md)** | Estado atual: pronto, em andamento, bloqueado | Para saber onde o projeto está hoje |
| **[08_Decisoes_e_Pendencias](08_Decisoes_e_Pendencias.md)** | Decisões já tomadas (e por quê) e o que falta decidir | Ao retomar o projeto ou decidir algo |
| **[09_Dominio_Nidum](09_Dominio_Nidum.md)** | Glossário do "jeito Nidum": motores, etiquetas, tríade, Intenção Reta | Para entender os termos próprios da Nidum |

## Como rodar / acessar (resumo)

- **Usar em produção:** acessar **https://chatnd.nidumbrasil.com.br** e fazer login (cadastro com aprovação manual do admin).
- **Subir/atualizar a plataforma:** ver **[02_Guia_de_Implantacao](02_Guia_de_Implantacao.md)**. Em resumo, há **dois caminhos**:
  1. **Mudanças no roteador ChatND e na ferramenta de arquivos** → publicadas **ao vivo via API** (sem derrubar o serviço).
  2. **Mudanças no código do backend** (frente Editorial, branding, Dockerfile) → vão por **git push → Railway reconstrói** (causa alguns minutos de indisponibilidade).
- **Mexer no código localmente:** o repositório está clonado em `C:\Users\daviv\dev\nidum-platform`. Ver o **[05_Guia_do_Contribuidor](05_Guia_do_Contribuidor.md)**.

> **Convenção deste pacote:** tudo que é específico da Nidum vive em pastas com prefixo `_nidum_` na raiz do repositório: `_nidum_docs/` (esta documentação), `_nidum_tools/` (código do roteador ChatND e da ferramenta de arquivos), `_nidum_manutencao/` (scripts de manutenção). O resto do repositório é o Open WebUI original.
