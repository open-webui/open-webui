# 05 — Guia do Contribuidor

> **Para quem é:** qualquer pessoa (ou agente de IA) que vá alterar o código deste repositório.
> **Quando consultar:** **antes** de editar qualquer arquivo, e antes de publicar uma mudança.

---

## Onde fica o quê

| Você quer mexer em... | Arquivo / pasta | Como publica |
|---|---|---|
| Comportamento do ChatND (roteamento, RAG, voz) | `_nidum_tools/chatnd_router.py` | API (ao vivo) |
| Geração de arquivos (PPTX/PDF/...) | `_nidum_tools/gerador_de_arquivos_nidum.py` | API (ao vivo) |
| Frente Editorial | `backend/open_webui/{models,routers,editorial}/...` | git push (rebuild) |
| Branding / imagem do contêiner | `backend/open_webui/static/`, `Dockerfile` | git push (rebuild) |
| Scripts de manutenção | `_nidum_manutencao/` | local (não vai pro app) |

> O repositório está clonado em `C:\Users\daviv\dev\nidum-platform` (**fora** do OneDrive, para não corromper o git).

## Regras que **nunca** devem ser quebradas

Cada uma corresponde a um bug real que já custou tempo:

1. **Código de ferramenta/roteador: APENAS ASCII.** Nada de bullets unicode (•), travessões (—) ou emojis dentro dos `.py` de `_nidum_tools/`. Copy-paste corrompe e quebra a sintaxe. Validar com `python -m py_compile <arquivo>`.
2. **Nunca usar `requests.post` para o próprio servidor** (localhost/domínio) dentro de uma tool. Causa *deadlock* do event loop → timeout. Usar os módulos internos: `from open_webui.storage.provider import Storage` e `from open_webui.models.files import Files`.
3. **A camada de arquivos é assíncrona.** `Files.insert_new_file(...)` é `async` → precisa de `await`. Esquecer disso grava o arquivo no disco mas **não** registra no banco → download dá 404.
4. **Nunca revelar qual IA/modelo está por trás** — em nenhum prompt, motor ou resposta.
5. **Nunca expor chaves/segredos** no chat, em logs ou em commits. Mascarar inclusive chaves aninhadas em dicts.
6. **`#não exclua nada` da Fonte:** os documentos fundadores **v29 e v30** precisam permanecer na base do ChatND. Não remover sem OK explícito.
7. **Não renomear um modelo base na UI** achando que cria um wrapper — gera duplicatas. Criar wrapper novo via `POST /api/v1/models/create`.
8. **Antes de excluir arquivos do volume:** fazer backup (inventário + bytes) e ter certeza de que são duplicados **por conteúdo** (SHA-256), não só por nome. (Ver `_nidum_manutencao/HIGIENE_DUPLICADOS.md`.)

## Como publicar uma mudança

### Roteador ChatND ou ferramenta (ao vivo)
1. Editar o `.py` em `_nidum_tools/`.
2. `python -m py_compile <arquivo>` (deve passar) + conferir que é **ASCII**.
3. Subir a versão no cabeçalho (`version: x.y.z`).
4. Publicar:
   - Roteador: `POST /api/v1/functions/id/chatnd/update` (com `id`, `name`, `meta`, `content`).
   - Ferramenta: `POST /api/v1/tools/id/gerador_de_arquivos_nidum/update`.
5. **Se mexeu só na ferramenta:** re-publicar **também** a função `chatnd` para zerar o cache do roteador.
6. Testar em produção (ex.: pedir um arquivo/uma resposta e conferir o resultado).
7. Guardar backup do conteúdo anterior (ex.: em `scratchpad/`).

### Backend (Editorial, branding, Dockerfile) — via git
1. Conferir dependências novas contra os pins existentes (especialmente `pillow==12.1.1`).
2. `git push origin main` → Railway reconstrói (**causa downtime**; evitar horário de uso).
3. Acompanhar **Build Logs**; verificar `/health` 200 e a migração aplicada no boot.

## Testes

- **Frente Editorial:** suite em `backend/open_webui/test/editorial/`, rodada pelo CI do GitHub Actions (`.github/workflows/editorial-ci.yml`) em **Python 3.11**, com cadeia de dependências enxuta (sem ML pesado).
  - O CI roda na branch de trabalho da Editorial (e por `workflow_dispatch`); a `main`/`dev`/tags disparam outros workflows. Logs de Actions exigem token; status/conclusão são públicos.
- **Roteador/ferramenta:** não há suite automatizada — a validação é por `py_compile` + **teste manual em produção** (gerar arquivo/resposta e conferir).
- **Ambiente local:** este PC usa Python 3.14, que quebra o import de `open_webui` (typer/click). Para rodar a suite editorial local: `pip install -U click typer uvicorn markdown beautifulsoup4 cryptography`, setar `WEBUI_SECRET_KEY` e `DATABASE_URL=sqlite`, então `cd backend && python -m pytest open_webui/test/editorial`.

## Como propor mudanças

- Trabalhar **fase por fase**, confirmando antes de cada passo que tenha efeito colateral, e explicando o "porquê" (o público inclui quem está começando).
- Para mudanças grandes no backend, usar uma **branch** própria e abrir PR; só dar merge na `main` quando o CI estiver verde (a `main` dispara deploy).
- Atualizar o **[07_Diario_e_Status](07_Diario_e_Status.md)** a cada sessão relevante (acrescentando, nunca apagando histórico) e registrar decisões no **[08_Decisoes_e_Pendencias](08_Decisoes_e_Pendencias.md)**.

## O que rodar antes de considerar "pronto"

- [ ] `py_compile` passou (para `.py` de `_nidum_tools/`).
- [ ] Conteúdo é ASCII (ferramentas/roteador).
- [ ] Nenhuma chave/segredo no diff.
- [ ] Testou o caminho feliz em produção (ou no CI, para a Editorial).
- [ ] Nenhuma das "regras que nunca devem ser quebradas" foi violada.
- [ ] Atualizou Diário/Status se foi uma mudança relevante.
