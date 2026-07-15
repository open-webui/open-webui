# -*- coding: ascii -*-
"""
Remove o REGISTRO privado do modelo-base 'claude-opus-4-8' no ChatND, para que ele
volte a ser "modelo cru" da conexao. Efeito (confirmado no codigo):
  - o motor (wrapper) passa a funcionar para o grupo (has_base_model_access libera
    base sem registro);
  - o opus-4-8 continua invisivel no seletor dos usuarios comuns (modelos sem
    registro so aparecem para admin).
Reversivel: a conexao continua fornecendo o opus-4-8; o registro pode ser recriado.

TRAVA DE SEGURANCA: por padrao SO PRE-VISUALIZA. Para excluir de verdade, defina
  $env:NIDUM_CONFIRMAR = "SIM"

USO:
  cd "C:\\Users\\daviv\\dev\\nidum-platform"
  $env:NIDUM_URL="https://chatnd.nidumbrasil.com.br"; $env:NIDUM_TOKEN="SEU_TOKEN_ADMIN"
  py _nidum_manutencao/remover_registro_opus.py            # pre-visualiza
  $env:NIDUM_CONFIRMAR="SIM"; py _nidum_manutencao/remover_registro_opus.py   # exclui
"""

import json
import os
import sys
import urllib.error
import urllib.request

MODEL_ID = "claude-opus-4-8"


def _http(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e)


def main():
    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    confirmar = os.environ.get("NIDUM_CONFIRMAR", "").strip().upper() == "SIM"
    if not base or not token:
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN. Veja o topo do arquivo.")
        sys.exit(1)

    # confirma que o alvo existe e mostra o estado atual
    st, body = _http("GET", "%s/api/v1/models" % base, token)
    if st != 200:
        print("Falha ao listar modelos (HTTP %d): %s" % (st, body[:200]))
        sys.exit(1)
    try:
        data = json.loads(body)
        models = data.get("data") if isinstance(data, dict) else data
    except Exception:
        print("Resposta nao-JSON."); sys.exit(1)

    alvo = None
    for m in (models or []):
        if str(m.get("id")) == MODEL_ID:
            alvo = m
            break
    if not alvo:
        print("O modelo %r nao esta na lista. Nada a fazer." % MODEL_ID)
        sys.exit(1)
    info = alvo.get("info") or {}
    grants = info.get("access_grants") or (info.get("meta") or {}).get("access_grants") or []
    print("Alvo: %s" % MODEL_ID)
    print("  tem registro (info): %s" % ("SIM" if info else "NAO"))
    print("  access_grants: %s" % (json.dumps(grants) if grants else "(vazio/privado)"))
    print("")

    if not info:
        print("Ja esta sem registro (modelo cru). Nada a excluir.")
        sys.exit(0)

    if not confirmar:
        print(">> PRE-VISUALIZACAO (nada foi alterado).")
        print(">> Para EXCLUIR o registro de fato, rode de novo com:")
        print('     $env:NIDUM_CONFIRMAR="SIM"')
        sys.exit(0)

    print("Excluindo o registro de %s ..." % MODEL_ID)
    st, body = _http("POST", "%s/api/v1/models/model/delete" % base, token, {"id": MODEL_ID})
    print("HTTP %d | resposta: %s" % (st, body[:200]))
    if st == 200 and "true" in body.lower():
        print("")
        print("OK. Registro removido. Agora:")
        print(" 1) Peca a um usuario do grupo para abrir o motor e gerar um relatorio.")
        print(" 2) Confirme que o opus-4-8 NAO aparece no seletor dele.")
        print("Se algo estranhar, o registro pode ser recriado em Admin -> Modelos.")
    else:
        print("Nao excluiu. Copie a resposta e mostre.")
        sys.exit(2)


if __name__ == "__main__":
    main()
