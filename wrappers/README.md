# wrappers/ — cópia canônica dos system prompts do ChatND

Os "wrappers" do ChatND são os **Models** do Open WebUI para onde o roteador (`_nidum_tools/chatnd.py`) encaminha cada pedido: `nidum-10---documentos`, `nidum-10---dia-a-dia`, `nidum-10---rpido`, `nidum-20---raciocinio`. O **system prompt** de cada um é um ativo crítico — define identidade, tom, regras de citação e segurança — mas hoje vive **só no painel** do Open WebUI (Workspace → Models → *System Prompt*), **sem histórico, sem revisão e sem backup**.

Esta pasta é a **cópia canônica versionada** desses prompts.

## Fonte da verdade e aplicação
- **Fonte da verdade = este repositório.** Toda mudança de prompt é feita **aqui**, por PR revisado.
- **Aplicação = manual, no painel.** Depois de mergeado, o texto do `.md` é **colado** no campo *System Prompt* do Model correspondente. Não há (ainda) automação que aplique isso pela API — e este repositório **não** deve tentar escrever no Open WebUI pela API.
- Enquanto não existir automação, a regra é simples: **o painel nunca diverge deste arquivo**. Mudou aqui (e mergeou) → cole no painel. Nunca edite direto no painel sem trazer a mudança para cá.

## Arquivos
| Arquivo | Model no painel |
|---|---|
| `chatnd_system_prompt.md` | `nidum-10---documentos` (rota de documentos / RAG) |

*(Os demais wrappers podem ser versionados aqui à medida que forem revisados.)*

## Como mudar um prompt
1. Edite o `.md` correspondente nesta pasta.
2. Abra um PR, revise e faça o merge.
3. Cole o novo texto no campo *System Prompt* do Model no painel (Workspace → Models → o wrapper → System Prompt → Save).

## Relação com o pipe (`_nidum_tools/chatnd.py`)
O pipe, na rota de documentos, injeta um lembrete de etiqueta/citação **na mensagem do usuário** (`_injetar_contexto`) — que só roda quando **houve** recuperação. Esse lembrete deve ficar **coerente** com o system prompt do wrapper aqui versionado: se um disser que `[Fora do acervo]` só vale quando nada foi recuperado, o outro não pode oferecer `[Fora do acervo]` como opção no caminho com contexto. Ao mudar a regra de etiqueta aqui, verifique o `_injetar_contexto` (e vice-versa).
