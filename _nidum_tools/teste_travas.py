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

    print("== TRAVA 3: _menciona_termo_canonico (vocabulario proprio da Nidum) ==")
    V = C.Pipe().valves.TERMOS_CANONICOS
    termos = C._termos_canonicos(V)

    # O SEPARADOR e o que impede a lista de se autodestruir: "fonte, forma e fluxo" tem
    # VIRGULAS. Numa valve separada por virgula, viraria tres termos - e "fonte" sozinho
    # dispararia em "qual a fonte dessa informacao?", ou seja, em quase tudo.
    ok &= check("separador ';': 'fonte, forma e fluxo' fica INTEIRO",
                "fonte, forma e fluxo" in termos)
    ok &= check("separador ';': 'fonte' NAO virou termo sozinho", "fonte" not in termos)
    ok &= check("'qual a fonte dessa informacao?' -> False (o pior falso positivo, evitado)",
                C._menciona_termo_canonico("qual a fonte dessa informacao?", V) is False)

    # O caso que motivou a trava: falhou DUAS vezes pelo prompt (1.31.0 e 1.33.0), com o
    # mesmo veredito no log (classificador='geral' = decisao dele, nao excecao).
    ok &= check("Q12: 'o que significa fazer da casa um ninho?' -> True",
                C._menciona_termo_canonico("o que significa fazer da casa um ninho?", V) is True)
    ok &= check("acento normalizado: 'Convergência' casa 'convergencia'",
                C._menciona_termo_canonico("o que foi a Convergência de junho?", V) is True)
    ok &= check("caixa ignorada: 'INTENÇÃO RETA' -> True",
                C._menciona_termo_canonico("me explica a INTENÇÃO RETA", V) is True)
    ok &= check("termo no meio da frase -> True",
                C._menciona_termo_canonico("como as comunidades vivas se organizam?", V) is True)
    ok &= check("limite de palavra: 'ninhosdemarimbondo' -> False",
                C._menciona_termo_canonico("ninhosdemarimbondo", V) is False)
    ok &= check("valve vazia -> False (nao casa tudo)",
                C._menciona_termo_canonico("fazer da casa um ninho", "") is False)
    ok &= check("texto vazio -> False", C._menciona_termo_canonico("", V) is False)
    ok &= check("None nao explode -> False", C._menciona_termo_canonico(None, V) is False)

    # Termo VAZIO casaria com QUALQUER texto e mandaria TUDO para a base. Entra por um
    # ';' a mais no fim da lista - digitado no painel, sem ninguem perceber.
    ok &= check("valve 'a;; b' -> nao gera termo vazio", "" not in C._termos_canonicos("a;; b"))
    ok &= check("valve 'ninho;' -> nao gera termo vazio", "" not in C._termos_canonicos("ninho;"))

    print("== TRAVA 3: FALSOS POSITIVOS ESPERADOS E ACEITOS (o custo, visivel) ==")
    # Estes NAO sao bugs - sao o PRECO da assimetria, aceito de olhos abertos. 'ninho',
    # 'regeneracao', 'ecossistema' e 'coautor' sao PORTUGUES COMUM, e o ChatND agora e
    # assistente geral: cada um custa uma resposta '[Fora do acervo]' onde havia de ser
    # resposta normal. Passam de proposito, para o custo ficar VISIVEL - se um dia
    # incomodar, o teste ja diz exatamente quais perguntas doem.
    ok &= check("CUSTO: 'vi um ninho de passarinho no quintal' -> vai para a base",
                C._menciona_termo_canonico("vi um ninho de passarinho no quintal", V) is True)
    ok &= check("CUSTO: 'o que e regeneracao celular?' -> vai para a base",
                C._menciona_termo_canonico("o que e regeneracao celular?", V) is True)
    ok &= check("CUSTO: 'o ecossistema de startups brasileiro' -> vai para a base",
                C._menciona_termo_canonico("o ecossistema de startups brasileiro", V) is True)
    ok &= check("CUSTO: 'quem e o coautor daquele livro?' -> vai para a base",
                C._menciona_termo_canonico("quem e o coautor daquele livro?", V) is True)
    # O contraponto que justifica o preco: conversa comum SEM termo segue em 'geral'.
    ok &= check("conversa comum sem termo -> False (a trava nao pega tudo)",
                C._menciona_termo_canonico("me ajude a escrever um email", V) is False)
    ok &= check("'qual a populacao de Americana-SP?' -> False",
                C._menciona_termo_canonico("qual a populacao de Americana-SP?", V) is False)

    print("== O BLOCO QUE ENSINA O CLASSIFICADOR (a frente da parafrase) ==")
    bloco = C._bloco_termos_no_prompt(V)
    ok &= check("cita os termos", "fazer da casa um ninho" in bloco)
    ok &= check("diz que e INFORMACAO, nao regra de estilo", "informacao" in bloco)
    ok &= check("valve vazia -> bloco vazio (nao polui o prompt a toa)",
                C._bloco_termos_no_prompt("") == "")

    print("== AS DUAS JUNTAS: o que a fronteira resgata ==")
    # Simula a decisao do roteador SEM chamar o classificador: dado que o LLM
    # devolveu 'geral' (o caso ruim), as travas corrigem?
    def resgata(texto):
        cat = "geral"
        if cat == "geral" and C._tem_marca_temporal(texto):
            cat = "documentos"
        if cat == "geral" and C._menciona_nidum(texto):
            cat = "documentos"
        if cat == "geral" and C._menciona_termo_canonico(texto, V):
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
    # O caso que motivou a trava 3: falhava DUAS vezes pelo prompt, agora e resgatado.
    ok &= check("Q12 RESGATADA pela trava 3: 'fazer da casa um ninho' -> documentos",
                resgata("o que significa fazer da casa um ninho?") == "documentos")
    # O BURACO QUE SOBRA, e ele encolheu mas nao fechou: pergunta institucional sem a
    # palavra 'Nidum', sem marca temporal e sem termo canonico depende SO do
    # classificador. Fica visivel aqui, e nao descoberto em producao.
    ok &= check("BURACO CONHECIDO: 'como funciona o EGP aqui?' -> geral (nenhuma trava "
                "alcanca; so o classificador salva)",
                resgata("como funciona o EGP aqui?") == "geral")
    ok &= check("conversa comum continua em geral",
                resgata("me ajude a escrever um email de agradecimento") == "geral")

    print("\nRESULTADO: " + ("TODAS AS TRAVAS OK" if ok else "HOUVE FALHA NUMA TRAVA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
