# 01 — PRD (Documento de Requisitos de Produto)

> **Para quem é:** quem precisa entender o "porquê" do produto — liderança, novos integrantes, e quem vai decidir prioridades.
> **Quando consultar:** para alinhar escopo, decidir o que entra/sai, e avaliar se algo proposto está dentro da visão.

---

## Problema que resolve

A Nidum precisa de uma plataforma de IA **própria e alinhada à sua filosofia**, em vez de depender de ferramentas genéricas (ChatGPT etc.) que:
- não conhecem os documentos, a linguagem e os princípios da Nidum;
- não garantem que os dados não sejam usados para treinar modelos externos;
- não falam na "voz" da Nidum nem respeitam a Intenção Reta (ver **[09_Dominio_Nidum](09_Dominio_Nidum.md)**).

O ChatND resolve isso sendo uma IA **da casa**: hospedada pela Nidum, ancorada na Fonte (documentos fundadores e livros), com identidade visual própria e regras de conduta alinhadas aos valores da organização.

## Usuário / persona

| Persona | Quem é | Necessidade principal |
|---|---|---|
| **Facilitador** (público inicial) | Pessoa da Academia/Nidum que conduz e dá feedback | Validar se a IA responde "no espírito Nidum" e gerar materiais |
| **Coautor interno** (público seguinte) | Integrante da Nidum (~dezenas de pessoas) | Tirar dúvidas ancoradas na Fonte, redigir, gerar arquivos on-brand |
| **Administrador** | Equipe de tecnologia | Operar, configurar e manter a plataforma no ar |

> A equipe que mantém a plataforma **não tem CTO dedicado nem time grande de infraestrutura**. Por isso os documentos são didáticos e o produto prioriza simplicidade operacional. (Origem: `PROMPT_MESTRE_PLATAFORMA_NIDUM_1.md`.)

## Escopo — o que **é**

1. **ChatND (motor de roteamento)** — recebe o pedido, classifica e encaminha para o motor certo, sem o usuário escolher. **(Pronto, em produção.)**
2. **Resposta ancorada na Fonte (RAG)** — busca nos documentos da Nidum e responde com base neles, com etiquetas de certeza. **(Pronto.)**
3. **Geração de arquivos on-brand** — PPTX, PDF, DOCX, XLSX, HTML e apresentação HTML navegável, com a identidade da marca. **(Pronto.)**
4. **Geração de imagens** — via motor oculto (Gemini), na estética da marca. **(Pronto, como recurso; integração total ao fluxo do ChatND em refinamento.)**
5. **Voz Nidum** — tríade fonte/forma/fluxo quando aplicável; nunca revelar qual IA está por trás; etiquetas de certeza. **(Pronto.)**
6. **Frente Editorial** — ingestão e export de obras + ficha viva por autor. **(Backend em produção; sem tela própria ainda — ver [07_Diario_e_Status](07_Diario_e_Status.md).)**

## Escopo — o que **não é** (fora de escopo, hoje)

- **Não** é um produto aberto ao público externo (essa é uma fase futura, não planejada agora).
- **Não** tem busca na web em tempo real (exigiria ferramenta de busca — fase futura).
- **Não** substitui o sistema editorial com tela dedicada (a Editorial é headless/API nesta rodada).
- **Não** expõe ao usuário qual modelo de IA (OpenAI/Anthropic/Google) está sendo usado — isso é regra inviolável.
- **Não** tem grupos/permissionamento fino ainda (hoje o controle é por aprovação manual de cadastro).

## Funcionalidades principais (estado real)

| Funcionalidade | Estado |
|---|---|
| Roteamento automático (6 rotas) | ✅ Pronto |
| RAG modo documento-inteiro + priorização dos fundadores | ✅ Pronto |
| Geração PPTX/PDF/DOCX/XLSX/HTML/Deck on-brand | ✅ Pronto |
| Geração de imagem (Gemini) | ✅ Pronto (recurso) |
| Tríade fonte/forma/fluxo (quando aplicável) | ✅ Pronto |
| Guardrails de segurança (anti-vazamento de prompt) | ✅ Pronto (mitigação, não garantia) |
| Editorial: ingestão .docx/.pdf/.epub/.odt | ✅ Backend pronto |
| Editorial: export .docx/.epub/.pdf | ✅ Backend pronto |
| Editorial: ficha viva por autor (F3) | ⚠️ Núcleo pronto; vínculo "modelo por projeto" pendente |
| Imagens embutidas nos exports editoriais (F2.4b) | ⏳ Planejado |
| Separação de memória (banco em Postgres) | ⏳ Planejado (prioridade 1) |
| Grupos/permissionamento | ⏳ Planejado |
| Integração SharePoint como fonte | ⏳ Planejado (futuro) |

## Critérios de sucesso

- **Quantidade de uso** da plataforma pelos coautores.
- **Feedback dos coautores** (especialmente facilitadores) sobre alinhamento à filosofia Nidum e utilidade.

> Não há métricas numéricas formais nem prazos definidos no momento. A evolução é guiada por feedback.

## Restrições conhecidas

- **Operacional:** roda em uma instância única no Railway com volume de 500 MB; uploads/indexação de PDFs grandes podem causar pico de memória (OOM). Custo da IA por pergunta de documento é aceito (~US$0,12 no motor de documentos).
- **Continuidade:** tudo deve estar no nome da empresa (contas, chaves, domínio), nunca de pessoa física. Chaves vivem no gerenciador de senhas (Bitwarden), nunca no chat nem no código.
