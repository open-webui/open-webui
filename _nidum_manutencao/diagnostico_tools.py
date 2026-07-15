# -*- coding: ascii -*-
"""
Diagnostico SO-LEITURA: por que "Tool not found".
Mostra:
  - do MOTOR (nidum-identificador-ambientes): a lista de ferramentas (toolIds) e o
    modo de function_calling;
  - das FERRAMENTAS (relatorio_ambientes_nidum, sharepoint_nidum): dono (user_id) e
    com quem estao compartilhadas (access_grants).

USO:
  cd "C:\\Users\\daviv\\dev\\nidum-platform"
  $env:NIDUM_URL="https://chatnd.nidumbrasil.com.br"; $env:NIDUM_TOKEN="SEU_TOKEN_ADMIN"
  py _nidum_manutencao/diagnostico_tools.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

MOTOR = "nidum-identificador-ambientes"
TOOLS = ("relatorio_ambientes_nidum", "sharepoint_nidum")


def _get(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer %s" % token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e)


def _lista(body):
    try:
        data = json.loads(body)
    except Exception:
        return []
    if isinstance(data, dict):
        return data.get("data") or data.get("models") or data.get("tools") or []
    return data if isinstance(data, list) else []


def main():
    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    if not base or not token:
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN.")
        sys.exit(1)

    # MOTOR
    st, body = _get("%s/api/v1/models" % base, token)
    models = _lista(body) if st == 200 else []
    motor = None
    for m in models:
        if str(m.get("id")) == MOTOR:
            motor = m
            break
    print("=== MOTOR: %s ===" % MOTOR)
    if not motor:
        print("  NAO ENCONTRADO.")
    else:
        info = motor.get("info") or {}
        meta = info.get("meta") or {}
        params = info.get("params") or {}
        print("  toolIds (ferramentas acopladas): %s" % json.dumps(meta.get("toolIds")))
        print("  capabilities: %s" % json.dumps(meta.get("capabilities")))
        print("  params.function_calling: %s" % params.get("function_calling"))
        print("  is_active: %s" % info.get("is_active"))
    print("")

    # TOOLS
    st, body = _get("%s/api/v1/tools" % base, token)
    tools = _lista(body) if st == 200 else []
    by_id = {str(t.get("id")): t for t in tools}
    for tid in TOOLS:
        print("=== TOOL: %s ===" % tid)
        t = by_id.get(tid)
        if not t:
            print("  NAO ENCONTRADA na lista de ferramentas.")
        else:
            grants = t.get("access_grants") or []
            print("  dono (user_id): %s" % t.get("user_id"))
            print("  access_grants: %s" % (json.dumps(grants) if grants else "(vazio = privado do dono)"))
        print("")

    print("Leitura: se o MOTOR estiver com toolIds vazio/null -> as ferramentas foram")
    print("desacopladas (reacoplar). Se as TOOLS tiverem access_grants vazio -> usuarios")
    print("do grupo nao conseguem usa-las (compartilhar com o grupo).")


if __name__ == "__main__":
    main()
