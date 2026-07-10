# 02 — Guia de Implantação

> **Para quem é:** quem vai colocar a plataforma no ar, atualizá-la ou reconfigurá-la.
> **Quando consultar:** antes de qualquer deploy, mudança de variável de ambiente ou publicação de código novo.

> ⚠️ **Regra de ouro:** chaves de API e senhas **nunca** entram no chat nem no código. Elas vivem no Bitwarden (pasta "Plataforma Nidum") e entram só como variáveis de ambiente no Railway ou no `.env.local` (que está no `.gitignore`).

---

## Visão geral: existem DOIS jeitos de publicar

Entender isto evita 90% da confusão:

| O que você mudou | Como publica | Causa indisponibilidade? |
|---|---|---|
| **Roteador ChatND** (`_nidum_tools/chatnd_router.py`) | API: `POST /api/v1/functions/id/chatnd/update` | ❌ Não (ao vivo) |
| **Ferramenta de arquivos** (`_nidum_tools/gerador_de_arquivos_nidum.py`) | API: `POST /api/v1/tools/id/gerador_de_arquivos_nidum/update` | ❌ Não (ao vivo) |
| **Prompt de um motor / valves** | API: `/api/v1/models/model/update` · `/api/v1/functions/id/chatnd/valves/update` | ❌ Não (ao vivo) |
| **Código do backend** (Editorial, branding, Dockerfile, fontes/logos na imagem) | `git push origin main` → Railway reconstrói | ✅ Sim (alguns minutos de 502) |

> **Lição importante:** o roteador ChatND mantém um *cache* do código da ferramenta. Ao atualizar **só** a ferramenta, pode não refletir — **re-publique o roteador** (`/functions/id/chatnd/update`) para zerar o cache. (Ver [05_Guia_do_Contribuidor](05_Guia_do_Contribuidor.md).)

---

## PARTE A — O que é pré-requisito **bloqueante** (sem isto, nada funciona)

Estes itens já existem e estão configurados. Esta lista serve para **recriar do zero** ou diagnosticar.

### A.1 Contas e credenciais (humano cria — não automatizável)
| Item | Onde | Observação |
|---|---|---|
| Conta **GitHub** (org `nidum-oficial-tec`) + 2FA | github.com | É a "chave mestra": o Railway loga via GitHub |
| Conta **Railway** (workspace `Nidum`) | railway.com | Login via GitHub; cartão + limite de gasto |
| Conta **OpenAI** + chave + **limite de gasto** | platform.openai.com | Data sharing desligado |
| Conta **Anthropic** + chave + limite | console.anthropic.com | — |
| **Bitwarden** (pasta "Plataforma Nidum") | bitwarden.com | Fonte única de credenciais |

### A.2 Variáveis de ambiente essenciais (no Railway)
| Variável | Valor | Quem seta |
|---|---|---|
| `OPENAI_API_KEY` | (do Bitwarden) | Humano, no painel |
| `ANTHROPIC_API_KEY` | (do Bitwarden) | Humano, no painel |
| `WEBUI_SECRET_KEY` | string aleatória de 64 caracteres (sem símbolos) | Humano |
| `WEBUI_NAME` | `Nidum AI` | CLI/painel |
| `ENABLE_SIGNUP` | `true` | CLI/painel |
| `DEFAULT_USER_ROLE` | `pending` (admin aprova cada usuário) | CLI/painel |
| `UVICORN_WORKERS` | `1` (mantém o app enxuto de memória) | CLI/painel |

> Lista completa e o significado de cada variável: **[04_Dicionario_de_Dados_e_Configuracao](04_Dicionario_de_Dados_e_Configuracao.md)**.

### A.3 Infraestrutura mínima
- [ ] **Volume persistente** montado em `/app/backend/data` (500 MB). Sem ele, os dados somem a cada deploy.
- [ ] **Domínio** `chatnd.nidumbrasil.com.br` apontado por CNAME (DNS no Registro.br) com SSL ativo.
- [ ] **Conta admin** criada (o primeiro usuário a se cadastrar vira admin).
- [ ] **`NIDUM_API_KEY`** (chave de API do próprio Open WebUI, gerada pelo admin) salva no `.env.local` local — necessária para publicar roteador/ferramenta via API.

### A.4 Checklist de deploy do backend (quando há mudança de código)
- [ ] Conferir que dependências novas **não conflitam** com `pillow==12.1.1` e demais pins existentes.
- [ ] `git push origin main` (ou `railway up --detach` para subir o código local).
- [ ] Acompanhar **Build Logs** no painel do Railway (build longo, ~8 min: baixa modelos).
- [ ] No boot, as migrações do banco rodam sozinhas (`alembic upgrade head`, controlado por `ENABLE_DB_MIGRATIONS`).
- [ ] Verificar `/health` (deve dar 200) e que a função `chatnd` continua ativa.
- [ ] **Evitar deploy em horário de uso** (o serviço fica ~minutos em 502 durante o rebuild).

---

## PARTE B — Integrações **opcionais / posteriores** (não bloqueiam o uso básico)

| Integração | Status | O que exige |
|---|---|---|
| **Geração de imagem (Gemini)** | ✅ Ativa | Billing no Google + `IMAGES_GEMINI_API_KEY` (modelo `imagen-4.0-generate-001`, método `predict`) |
| **Storage S3/R2** (para a Editorial escalar) | ⏳ Planejado | Bucket S3-compatível + `STORAGE_PROVIDER=s3` + credenciais |
| **Banco em Postgres** (separação de memória) | ⏳ Planejado (prioridade 1) | Provisionar Postgres no Railway + `DATABASE_URL` + migração dos dados |
| **SharePoint como fonte** | ⏳ Futuro | App no Azure AD + Microsoft Graph + job de sync |

> **Atenção (chaves no app):** o Open WebUI guarda algumas chaves **no banco**, não na variável de ambiente, após o boot. Ao **rotacionar a chave da OpenAI**, é preciso **reiniciar o serviço** (a função de embedding cacheia a chave no boot) **e** atualizar a chave dentro do app (Configurações → Conexões/Documentos/Imagens). Caso contrário o RAG quebra com erro 401.

---

## Diagnóstico rápido

| Sintoma | Causa provável | Ação |
|---|---|---|
| ChatND fora do ar / 502 | Rebuild em andamento, ou crédito Railway acabou | Aguardar build; conferir billing no Railway |
| Geração de arquivo falha com "No space left on device" | Volume cheio | Liberar espaço (ver `_nidum_manutencao/`) ou ampliar volume |
| OOM / crash ao subir PDF grande | Pico de RAM na indexação | Subir 1 arquivo por vez; resolver = mais memória (billing) |
| RAG responde "não consta" indevidamente | Chave de embedding inválida após rotação | Reiniciar serviço + atualizar chave no app |
| Arquivo gerado sai sem identidade da marca | Cache do roteador com a ferramenta antiga | Re-publicar a função `chatnd` |
