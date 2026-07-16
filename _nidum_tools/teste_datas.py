# -*- coding: utf-8 -*-
"""
Prova AUTOMATICA e SEM RISCO da normalizacao de datas na busca (_expandir_datas do
chatnd.py). Exercita so a funcao PURA - nao faz rede, nao busca, nao toca na base.
Sai != 0 se qualquer caso decidir errado.

Por que aqui e nao no teste_freios.py da esteira: aquele arquivo vive em OUTRO
repositorio (nidum-chatnd-basefonte) e nao consegue importar o chatnd.py, que depende
do open_webui. Aqui stubamos o open_webui (MagicMock) so para conseguir importar o
modulo e testar as funcoes puras - nenhum codigo do app e executado.

USO: python _nidum_tools/teste_datas.py
"""

import datetime
import os
import sys
from unittest.mock import MagicMock

# Stub do open_webui: permite importar o chatnd.py fora do app. As funcoes testadas
# aqui sao PURAS e nao tocam em nada disto.
for _m in [
    "open_webui", "open_webui.utils", "open_webui.utils.chat", "open_webui.models",
    "open_webui.models.users", "open_webui.models.knowledge", "open_webui.retrieval",
    "open_webui.retrieval.utils", "open_webui.utils.plugin",
]:
    sys.modules[_m] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatnd as C  # noqa: E402

HOJE = datetime.date(2026, 7, 16)   # relogio FIXO: teste nao pode depender do dia real


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def tem(texto, *partes):
    return all(p in texto for p in partes)


def main():
    ok = True

    print("== CASO REAL DA Q14 (a pergunta diz '13/07'; o arquivo e ..._13072026.md e o corpo '13 de julho de 2026') ==")
    r = C._expandir_datas("resuma a reuniao de 13/07", HOJE)
    ok &= check("13/07 -> variante do NOME do arquivo (13072026)", "13072026" in r)
    ok &= check("13/07 -> variante do CORPO (13 de julho de 2026)", "13 de julho de 2026" in r)
    ok &= check("13/07 -> demais variantes (barras/hifen/ponto/ISO)",
                tem(r, "13/07/2026", "13-07-2026", "13.07.2026", "2026-07-13"))
    ok &= check("13/07 -> a pergunta original continua no texto", r.startswith("resuma a reuniao de 13/07"))

    print("== OUTROS FORMATOS DE ENTRADA ==")
    r = C._expandir_datas("reuniao de 13 de julho de 2026", HOJE)
    ok &= check("por extenso -> gera compacta e barras", tem(r, "13072026", "13/07/2026"))
    r = C._expandir_datas("ata de 2026-07-13", HOJE)
    ok &= check("ISO -> gera compacta e barras", tem(r, "13072026", "13/07/2026"))
    r = C._expandir_datas("ata 13072026", HOJE)
    ok &= check("compacta -> gera por extenso", "13 de julho de 2026" in r)
    r = C._expandir_datas("reuniao de 13/jul", HOJE)
    ok &= check("abreviada (13/jul) -> gera compacta", "13072026" in r)
    r = C._expandir_datas("reuniao de 13.07.2026", HOJE)
    ok &= check("pontos -> gera compacta", "13072026" in r)

    print("== ANO: explicito vence a heuristica; ausente usa data PASSADA ==")
    r = C._expandir_datas("assuntos da reuniao de 25/12/2027", HOJE)
    ok &= check("ano explicito (25/12/2027) -> usa 2027, nao a heuristica",
                "25122027" in r and "25122026" not in r)
    r = C._expandir_datas("reuniao de 13/07", HOJE)
    ok &= check("sem ano, data ja passou -> ano corrente (2026)", "13072026" in r)
    r = C._expandir_datas("reuniao de 13/12", HOJE)
    ok &= check("sem ano, data no futuro -> ano anterior (2025)",
                "13122025" in r and "13122026" not in r)

    print("== NAO EXPANDE (sem data / data impossivel) ==")
    t = "qual o proposito da Nidum?"
    ok &= check("sem data -> texto INALTERADO", C._expandir_datas(t, HOJE) == t)
    t = "reuniao de 32/13/2026"
    ok &= check("data impossivel (32/13) -> INALTERADO", C._expandir_datas(t, HOJE) == t)
    t = "reuniao de 31/02/2026"
    ok &= check("data impossivel (31/02) -> INALTERADO", C._expandir_datas(t, HOJE) == t)
    ok &= check("texto vazio -> intacto", C._expandir_datas("", HOJE) == "")

    print("== IDEMPOTENCIA ==")
    uma = C._expandir_datas("resuma a reuniao de 13/07", HOJE)
    duas = C._expandir_datas(uma, HOJE)
    ok &= check("expandir 2x nao duplica variantes", uma == duas)
    ok &= check("cada variante aparece 1x", duas.count("13072026") == 1)

    print("\nRESULTADO: " + ("NORMALIZACAO DE DATAS OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
