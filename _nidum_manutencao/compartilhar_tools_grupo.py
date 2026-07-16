# -*- coding: ascii -*-
"""
Compartilha as ferramentas do motor Ambientes com o grupo 'identificador-ambientes'
(permissao de LEITURA/uso), corrigindo o "Tool not found" no modo Native.

Nao muda o codigo das tools; so o controle de acesso (igual ao que foi feito no motor).

TRAVA DE SEGURANCA: por padrao SO PRE-VISUALIZA. Para aplicar de verdade:
  $env:NIDUM_CONFIRMAR = "SIM"

USO:
  cd "C:\\Users\\daviv\\dev\\nidum-platform"
  $env:NIDUM_URL="https://chatnd.nidumbrasil.com.br"; $env:NIDUM_TOKEN="SEU_TOKEN_ADMIN"
  py _nidum_manutencao/compartilhar_tools_grupo.py            # pre-visualiza
  $env:NIDUM_CONFIRMAR="SIM"; py _nidum_manutencao/compartilhar_tools_grupo.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

TOOLS = ("relatorio_ambientes_nidum", "sharepoint_nidum")
GRUPO_ID = os.environ.get("NIDUM_GRUPO_ID", "713dd53e-eb6c-46b5-bd59-5a45972460a3")
GRUPO_NOME = "identificador-ambientes"


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
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN.")
        sys.exit(1)

    # valida que o grupo existe e o nome bate
    st, body = _http("GET", "%s/api/v1/groups/" % base, token)
    grupos = []
    if st == 200:
        try:
            data = json.loads(body)
            grupos = data if isinstance(data, list) else data.get("data", [])
        except Exception:
            pass
    alvo = None
    for g in grupos:
        if str(g.get("id")) == GRUPO_ID or str(g.get("name", "")).strip().lower() == GRUPO_NOME:
            alvo = g
            break
    if not alvo:
        print("ERRO: grupo %r (id %s) nao encontrado. Grupos vistos: %s"
              % (GRUPO_NOME, GRUPO_ID, ", ".join(repr(g.get("name")) for g in grupos) or "(nenhum)"))
        sys.exit(1)
    gid = str(alvo.get("id"))
    print("Grupo alvo: %s (id %s)" % (alvo.get("name"), gid))
    print("Tools alvo: %s" % ", ".join(TOOLS))
    print("Permissao a conceder: read (usar a ferramenta; sem editar)")
    print("")

    if not confirmar:
        print(">> PRE-VISUALIZACAO (nada foi alterado).")
        print(">> Para APLICAR: $env:NIDUM_CONFIRMAR=\"SIM\" e rode de novo.")
        sys.exit(0)

    grants = [{"principal_type": "group", "principal_id": gid, "permission": "read"}]
    falhas = 0
    for tid in TOOLS:
        st, body = _http("POST", "%s/api/v1/tools/id/%s/access/update" % (base, tid),
                         token, {"access_grants": grants})
        ok = False
        if st == 200:
            try:
                j = json.loads(body)
                ags = j.get("access_grants") or []
                ok = any(a.get("principal_id") == gid for a in ags)
            except Exception:
                pass
        print("%s -> HTTP %d %s" % (tid, st, "OK (grupo com leitura)" if ok else "| " + body[:200]))
        if not ok:
            falhas += 1

    print("")
    if falhas == 0:
        print("PRONTO. As duas tools estao compartilhadas com o grupo.")
        print("Teste: conversa NOVA com o motor -> foto -> gerar relatorio.")
    else:
        print("Houve falha em %d tool(s). Copie a saida e me mostre." % falhas)
        sys.exit(2)


if __name__ == "__main__":
    main()
