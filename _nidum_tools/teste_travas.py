# -*- coding: utf-8 -*-
"""
Prova AUTOMATICA das TRAVAS DETERMINISTICAS do roteador. Sao elas que seguram o
desenho de UMA fronteira ("e da Nidum?"): quando o classificador LLM erra, sao as
travas que resgatam a pergunta institucional antes de ela virar resposta inventada
- ou, com a fatia 3, resposta do Google sobre uma empresa homonima.

Trava nao testada e esperanca, nao protecao. (Mesma licao do teste_freios.py da
esteira, que em 16/07 pegou um fail-silent que a revisao de codigo nao pegou.)

Testa funcoes PURAS - nao chama modelo, nao busca, nao toca em rede.

USO: py _nidum_tools/teste_travas.py
"""

import os
import sys
from unittest.mock import MagicMock

# Stub do open_webui: permite importar o chatnd.py fora do app. As funcoes testadas
# aqui sao PURAS e nao tocam em nada disto. Mesmo padrao do teste_datas.py.
# A lista nao e adivinhada - saiu de:
#     grep -oE "from (open_webui[a-z_.]*) import" _nidum_tools/chatnd.py
# mais os pacotes-pai de cada um (o Python precisa deles no sys.modules).
for _m in [
    "open_webui",
    "open_webui.models", "open_webui.models.knowledge", "open_webui.models.users",
    "open_webui.retrieval", "open_webui.retrieval.utils",
    "open_webui.routers", "open_webui.routers.images",
    "open_webui.utils", "open_webui.utils.chat", "open_webui.utils.plugin",
]:
    sys.modules[_m] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatnd as C  # noqa: E402


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def main():
    ok = True

    print("== TRAVA 2: _menciona_nidum (a pessoa escreveu o nome) ==")
    # O caso que motivou a trava: se isto cair em 'geral' com web, volta uma
    # empresa homonima do Google, com confianca e citacao.
    ok &= check("'qual o proposito da Nidum?' -> True",
                C._menciona_nidum("qual o proposito da Nidum?") is True)
    ok &= check("caixa nao importa: 'NIDUM' -> True",
                C._menciona_nidum("o que a NIDUM entende por regeneracao") is True)
    ok &= check("'nidum' minusculo -> True",
                C._menciona_nidum("me fala da nidum") is True)
    ok &= check("no meio da frase -> True",
                C._menciona_nidum("como funciona a governanca na Nidum hoje?") is True)

    # \b nas duas pontas: sem isso, qualquer palavra CONTENDO 'nidum' dispararia a
    # trava e mandaria conversa comum para a base - custo pequeno, mas e ruido que
    # some sozinho com a fronteira de palavra.
    ok &= check("dominio 'chatnd.nidumbrasil.com.br' -> False (nao e palavra inteira)",
                C._menciona_nidum("o site chatnd.nidumbrasil.com.br esta fora do ar?") is False)
    ok &= check("palavra colada ('nidumzinho') -> False",
                C._menciona_nidum("nidumzinho") is False)

    # Negativos: conversa que nao cita a Nidum segue em 'geral'. Se estes derem
    # True, a trava vira "tudo vai para a base" e a rota 'geral' morre na pratica.
    ok &= check("'qual a populacao de Americana-SP?' -> False",
                C._menciona_nidum("qual a populacao de Americana-SP?") is False)
    ok &= check("'explique a diferenca entre SPE e SCP' -> False (sem citar Nidum)",
                C._menciona_nidum("explique a diferenca entre SPE e SCP") is False)
    ok &= check("saudacao -> False", C._menciona_nidum("bom dia!") is False)
    ok &= check("vazio -> False", C._menciona_nidum("") is False)
    ok &= check("None nao explode -> False", C._menciona_nidum(None) is False)

    print("== TRAVA 1: _tem_marca_temporal (nao regrediu) ==")
    # O bug real que originou a trava (Q14): "reuniao de 08/07" caiu em conversa e
    # nunca chegou a base.
    ok &= check("'o que a reuniao de 08/07 decidiu?' -> True",
                C._tem_marca_temporal("o que a reuniao de 08/07 decidiu?") is True)
    ok &= check("'ata' -> True", C._tem_marca_temporal("me manda a ata") is True)
    ok &= check("'quando' -> True", C._tem_marca_temporal("quando foi isso?") is True)
    ok &= check("'convergencia' -> True",
                C._tem_marca_temporal("a convergencia de Comunidades Vivas") is True)
    ok &= check("data por extenso -> True",
                C._tem_marca_temporal("o de 8 de junho de 2026") is True)
    ok &= check("'bom dia' -> False", C._tem_marca_temporal("bom dia") is False)

    print("== AS DUAS JUNTAS: o que a fronteira resgata ==")
    # Simula a decisao do roteador SEM chamar o classificador: dado que o LLM
    # devolveu 'geral' (o caso ruim), as travas corrigem?
    def resgata(texto):
        cat = "geral"
        if cat == "geral" and C._tem_marca_temporal(texto):
            cat = "documentos"
        if cat == "geral" and C._menciona_nidum(texto):
            cat = "documentos"
        return cat

    ok &= check("classificador errou 'qual o proposito da Nidum?' -> resgatado p/ documentos",
                resgata("qual o proposito da Nidum?") == "documentos")
    ok &= check("classificador errou 'reuniao de 13/07' -> resgatado p/ documentos",
                resgata("o que foi tratado na reuniao de 13/07?") == "documentos")
    ok &= check("'quais os valores da Nidum, segundo a Fonte?' -> documentos",
                resgata("quais os valores da Nidum, segundo a Fonte?") == "documentos")
    # O buraco conhecido e ACEITO: pergunta institucional sem a palavra 'Nidum' e
    # sem marca temporal depende SO do classificador. Ex.: "como funciona o EGP
    # aqui?". Esta linha existe para o buraco ficar VISIVEL no teste, e nao ser
    # descoberto por acidente em producao.
    ok &= check("BURACO CONHECIDO: 'como funciona o EGP aqui?' -> geral (so o "
                "classificador salva; as travas nao alcancam)",
                resgata("como funciona o EGP aqui?") == "geral")
    ok &= check("conversa comum continua em geral",
                resgata("me ajude a escrever um email de agradecimento") == "geral")

    print("\nRESULTADO: " + ("TODAS AS TRAVAS OK" if ok else "HOUVE FALHA NUMA TRAVA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
