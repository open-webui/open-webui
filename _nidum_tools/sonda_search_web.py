"""
title: SONDA 2 - search_web com usuario NAO-ADMIN (DESCARTAVEL)
author: Nidum
version: 0.1.0
description: SONDA DESCARTAVEL. Nao e produto. Prova o UNICO caminho que a fatia 3 pode usar - search_web (a camada de baixo, sem gate de permissao) - e prova com usuario NAO-ADMIN, que e o caso real. A sonda 1 provou process_web_search como ADMIN e isso nao serve: process_web_search da 403 para coautor. APAGAR do painel e do repo assim que responder.
"""

# =============================================================================
# POR QUE ESTA SONDA E DIFERENTE DA SONDA 1
#
# A sonda 1 (sonda_web_search) provou que process_web_search RODA dentro do pipe -
# mas rodou como ADMIN, e ao investigar o 403 dela apareceu o que muda tudo:
#
#     process_web_search checa a permissao DENTRO da funcao (routers/retrieval.py):
#       2216  if not ENABLE_WEB_SEARCH:                      -> 403
#       2222  if user.role != 'admin' and not has_permission(...): -> 403
#
# A permissao "Pesquisa na Web" fica OFF DE PROPOSITO (defesa em duas camadas). Entao
# process_web_search daria 403 para TODO COAUTOR. O pipe chama como o coautor (nao-admin).
# Por isso o desenho da fatia 3 NAO pode usar process_web_search - tem que usar a camada
# de baixo, search_web (routers/retrieval.py:1889), que NAO tem gate de permissao nem de
# ENABLE_WEB_SEARCH.
#
# ESTA SONDA PROVA EXATAMENTE ISSO, e so isso: que search_web roda, a partir do pipe, com
# um usuario NAO-ADMIN. Se rodar como admin, nao prova nada novo (a sonda 1 ja fez).
#
# O QUE MUDOU NO ENTENDIMENTO (registrado aqui porque a sonda 1 assumia o contrario):
# search_web devolve list[SearchResult] CRU (link/title/snippet). NAO tem etapa de
# embedding, NAO chama save_docs_to_vector_db, NAO passa pelo branch do BYPASS_WEB_SEARCH_
# EMBEDDING_AND_RETRIEVAL. Aquele BYPASS vive DENTRO do process_web_search - o caminho que
# NAO vamos usar. Ou seja: a config "Ignorar Embedding e Recuperacao" e IRRELEVANTE para a
# fatia 3. Esta sonda confirma isso de quebra, mostrando o formato do retorno.
#
# COMO USAR - E O PONTO CRITICO:
#   1. Publicar como Function (Pipe). NAO anexar a modelo nenhum.
#   2. LOGAR COMO UM COAUTOR NAO-ADMIN (ou pedir para um coautor rodar). Se rodar como
#      admin, a sonda AVISA no resultado e o teste nao vale.
#   3. Selecionar "SONDA 2 - search_web" e perguntar algo factual: "populacao de Americana SP".
#   4. Ler o resultado no chat E o log do Railway (linhas "sonda2:").
#   5. APAGAR a function do painel e a branch. E apagar tambem a sonda 1, que ainda esta
#      publicada.
#
# VEREDITO:
#   [OK] passo 2 com role != admin  -> search_web roda para coautor. Fatia 3 VIAVEL.
#   [FALHA]                          -> o traceback diz por que; a fatia 3 muda ou espera.
# =============================================================================

import logging
import traceback

log = logging.getLogger(__name__)

from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        MAX_CHARS_AMOSTRA: int = Field(default=1500)

    def __init__(self):
        self.type = "pipe"
        self.id = "sonda_search_web"
        self.name = "SONDA 2 - search_web nao-admin (descartavel)"
        self.valves = self.Valves()

    async def pipe(self, body: dict, __user__=None, __request__=None):
        linhas = []

        def diz(txt):
            log.info("sonda2: %s", txt)
            linhas.append(txt)

        # --- QUEM esta rodando? Se for admin, o teste nao prova o caso real -----
        # A sonda 1 falhou justamente por rodar como admin. Este passo existe para a
        # sonda nao se enganar de novo: ela SO vale com role != admin.
        papel = "?"
        try:
            papel = (__user__ or {}).get("role", "?")
        except Exception:
            pass
        diz("usuario role=%r" % papel)
        if papel == "admin":
            diz("[ATENCAO] voce esta como ADMIN. Este teste SO PROVA ALGO com um usuario "
                "NAO-ADMIN (coautor). Como admin, o resultado abaixo nao distingue nada "
                "da sonda 1. Rode de novo logado como coautor.")
            # segue mesmo assim, para pelo menos exercitar o import e a chamada

        # --- a pergunta -------------------------------------------------------
        msgs = body.get("messages") or []
        pergunta = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                c = m.get("content")
                pergunta = c if isinstance(c, str) else " ".join(
                    str(x.get("text", "")) for x in (c or []) if isinstance(x, dict)
                )
                break
        if not pergunta.strip():
            return "SONDA 2: mande uma pergunta factual, ex.: 'populacao de Americana SP'."
        diz("pergunta=%r" % pergunta[:120])

        # --- PASSO 0: import de search_web de dentro do pipe ------------------
        try:
            from open_webui.routers.retrieval import search_web
            diz("[OK] passo 0 - import de search_web funcionou")
        except Exception as e:
            diz("[FALHA] passo 0 - nao consegui importar search_web: %r" % e)
            diz(traceback.format_exc()[:900])
            return "\n".join(linhas)

        # --- que engine esta configurada? (a pergunta do dropdown DDGS) -------
        engine = None
        try:
            engine = __request__.app.state.config.WEB_SEARCH_ENGINE
            diz("[info] WEB_SEARCH_ENGINE=%r (o dropdown 'DDGS' grava 'duckduckgo')" % engine)
        except Exception as e:
            diz("[info] nao li a engine (%r)" % e)

        # --- PASSO 1: A PERGUNTA DA SONDA ------------------------------------
        # Chamada IDENTICA a que o process_web_search faz internamente
        # (routers/retrieval.py:2247), so que feita DIRETO, de dentro do pipe, PULANDO os
        # dois gates (permissao e ENABLE_WEB_SEARCH). Passa o __user__ do PIPE - o coautor.
        try:
            resultados = await search_web(
                __request__,
                engine or "duckduckgo",
                pergunta,
                __user__,
            )
            diz("[OK] passo 1 - search_web RODOU de dentro do pipe, com role=%r" % papel)
        except Exception as e:
            diz("[FALHA] passo 1 - search_web levantou: %r" % e)
            diz(traceback.format_exc()[:1500])
            return "\n".join(linhas)

        # --- PASSO 2: o que voltou? ------------------------------------------
        # search_web devolve list[SearchResult] (link/title/snippet), CRU. Se este for o
        # formato, a fatia 3 monta o contexto do snippet direto - sem vetor, sem BYPASS.
        if not resultados:
            diz("[ATENCAO] rodou mas devolveu LISTA VAZIA - sem erro, sem resultado. Pode "
                "ser rate-limit do DDGS ou pergunta ruim; tente outra factual.")
            return "\n".join(linhas)

        diz("[OK] passo 2 - voltaram %d resultado(s), tipo do primeiro=%s"
            % (len(resultados), type(resultados[0]).__name__))

        # --- PASSO 3: amostra, para o humano julgar se achou a coisa certa ----
        amostra = []
        for r in resultados[:3]:
            titulo = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "")
            link = getattr(r, "link", None) or (r.get("link") if isinstance(r, dict) else "")
            trecho = getattr(r, "snippet", None) or (r.get("snippet") if isinstance(r, dict) else "")
            amostra.append("- %s\n  %s\n  %s" % (titulo, link, (trecho or "")[:300]))
        if amostra:
            diz("--- amostra ---")
            diz("\n".join(amostra)[: self.valves.MAX_CHARS_AMOSTRA])

        diz("")
        if papel != "admin":
            diz("=== VEREDITO: '[OK] passo 1' com role != admin -> o pipe aciona "
                "search_web para um COAUTOR. A fatia 3 e viavel pelo caminho certo. ===")
        else:
            diz("=== INCONCLUSIVO: rodou como admin. Rode como coautor para valer. ===")
        return "\n".join(linhas)
