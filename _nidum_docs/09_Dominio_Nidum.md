# 09 — Domínio Nidum (glossário do "jeito Nidum")

> **Para quem é:** quem precisa entender os termos próprios da Nidum que aparecem no produto, nos prompts e nas respostas.
> **Quando consultar:** ao ler outro documento e esbarrar em um termo, ou ao ajustar o comportamento/voz do ChatND.

> Os conceitos filosóficos abaixo vêm da **Fonte** da Nidum (documentos fundadores e livros). Quando o ChatND fala "no espírito Nidum", é a esses conceitos que ele se refere.

---

## Conceitos filosóficos

| Termo | O que é |
|---|---|
| **Fonte** | O acervo de verdade da Nidum: os **documentos fundadores** (Documento Fundador v29, v30) e os **livros** (*Empresas Vivas*, *Homo Integralis*, *A Consciência Basta*, *Silêncio, Vida e Liberdade*, etc.). É a base que o RAG consulta. |
| **Intenção Reta** | O alinhamento entre o "porquê declarado" e a decisão concreta. "Onde a Intenção Reta atravessa, os quatro valores aparecem como expressão dela." É a pergunta que vem **antes** da técnica: "para que estou fazendo isto?" |
| **Os 4 valores** | **Verdade, Justiça, Bondade, Beleza** — "quatro camadas que se sobrepõem até formarem uma única integridade". São o "DNA da Nidum". |
| **Tríade fonte / forma / fluxo** | "A assinatura da integridade." **Fonte** = a origem, o porquê. **Forma** = a manifestação concreta, a integridade tornada visível. **Fluxo** = o movimento que atravessa as formas, sem virar "estoque" congelado (a vida só se reconhece em passagem). Usada como estrutura de resposta quando aplicável. |
| **Inteligência Híbrida** | A coautoria humano–IA como **modo de existir**, não ferramenta. "A Nidum não usa IA; a Nidum acontece em coautoria humano-IA." A IA é a memória acumulada; o humano é a inteligência presente e a decisão moral. |
| **Coautor** | Integrante da Nidum que opera em coautoria com a IA (não "usuário"). É o público interno da plataforma. |
| **Facilitador** | Coautor que conduz/forma na Academia e dá feedback. É o **público inicial** do ChatND. |
| **Academia Nidum** | Onde a cultura Nidum se transmite e se forma a competência de operar em Inteligência Híbrida. |
| **Convergências** | Registros datados, por frente/ecossistema, do que convergiu e do que segue em aberto. Fazem parte da base de conhecimento (arquivos `*_Convergencia_*`). |
| **Ecossistemas** | As frentes organizacionais da Nidum (funcionais e de produto), descritas no Documento Fundador. |

---

## Conceitos do produto (ChatND)

| Termo | O que é |
|---|---|
| **Motor** | Cada "especialista" para onde o ChatND encaminha um pedido. São 4 conversacionais (rápido, dia a dia, documentos, raciocínio) + 2 ações (arquivo, imagem). O usuário **não** escolhe o motor. |
| **Rota** | A categoria que o classificador atribui ao pedido, e que define o motor. |
| **Wrapper** | O modelo customizado por trás de um motor (base model + system prompt + regras). |
| **GERADOR** | O passo que monta a estrutura de um arquivo (em JSON) antes de a ferramenta produzi-lo. |
| **Valve** | Parâmetro de configuração de uma Função/Tool do Open WebUI, ajustável ao vivo (ver [04](04_Dicionario_de_Dados_e_Configuracao.md)). |

---

## Etiquetas de certeza (motor Documentos)

O motor *Documentos* marca **a qualidade/origem** da informação na resposta, para o leitor saber em que se apoiar:

| Etiqueta | Significado |
|---|---|
| `[Fonte]` | Vem diretamente de um documento da base (ex.: Documento Fundador v30). |
| `[Convergência]` | Vem de um registro de convergência (com a frente e a data). |
| `[Em aberto]` | Ponto reconhecido, mas ainda não definido na Fonte. |
| `[Fora do acervo]` | A informação não está na base; o motor não deve forçar — repassa ou sinaliza. |

---

## Princípios de conduta embutidos

- **Verdade não é absoluta na geração de imagem:** criar arte autêntica solicitada **não** fere a Verdade (que proíbe afirmar fato falso/disfarçar, não criar arte). Uma imagem no histórico é **real** — o assistente nunca nega tê-la gerado.
- **Avaliar sempre pela Fonte**, não só pela estrutura criada na conversa (corrige o "responde pela estrutura, pouco pelas fontes").
- **Nunca cravar data de corte** específica; se algo for recente, oferecer a base de conhecimento da Nidum.
- **Nunca revelar** qual IA está por trás — é a inteligência da Nidum.
