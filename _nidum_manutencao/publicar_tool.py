# -*- coding: ascii -*-
"""
Publica (ou atualiza) QUALQUER tool na imagem VIVA do ChatND, a partir do .py local.

O id da tool = nome do arquivo (sem .py). O nome/descricao saem do cabecalho (title/
description) do proprio arquivo. Confere se a URL e mesmo o ChatND e valida a resposta.

COMO USAR (no seu terminal):
  1) variaveis de ambiente:
       $env:NIDUM_URL   = "https://chatnd.nidumbrasil.com.br"
       $env:NIDUM_TOKEN = "SEU_TOKEN_ADMIN"
  2) rode passando o caminho do .py:
       py _nidum_manutencao/publicar_tool.py _nidum_tools/sharepoint_nidum.py

Se a tool ja existir, atualiza (nao duplica). So-ASCII.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request


def _http(method, url, token, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e)


def _parece_html(txt):
    t = (txt or "").lstrip().lower()
    return t.startswith("<!doctype") or t.startswith("<html")


def _cabecalho(campo, texto):
    m = re.search(r"(?im)^\s*%s\s*:\s*(.+)$" % re.escape(campo), texto)
    return m.group(1).strip() if m else ""


def main():
    if len(sys.argv) < 2:
        print("USO: py _nidum_manutencao/publicar_tool.py <caminho-do-arquivo.py>")
        sys.exit(1)
    code_path = sys.argv[1]
    if not os.path.isfile(code_path):
        print("ERRO: arquivo nao encontrado: %s" % code_path)
        sys.exit(1)

    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    if not base or not token:
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN. Veja o topo do arquivo.")
        sys.exit(1)

    print("Conferindo a URL: %s" % base)
    st0, body0 = _http("GET", "%s/api/config" % base, token)
    if _parece_html(body0) or st0 != 200:
        print("ERRO: essa URL nao respondeu como o ChatND (HTTP %d%s)." % (
            st0, ", pagina HTML" if _parece_html(body0) else ""))
        print('Ajuste: $env:NIDUM_URL = "https://chatnd.nidumbrasil.com.br"')
        sys.exit(1)
    print("URL confere.")

    with open(code_path, "r", encoding="ascii") as fh:
        content = fh.read()
    tool_id = os.path.splitext(os.path.basename(code_path))[0].lower()
    name = _cabecalho("title", content) or tool_id
    desc = _cabecalho("description", content)[:400] or name
    print("Publicando tool id=%s (%d bytes)..." % (tool_id, len(content)))

    form = {"id": tool_id, "name": name, "content": content, "meta": {"description": desc}}
    st, body = _http("POST", "%s/api/v1/tools/create" % base, token, form)
    if st != 200:
        print("create HTTP %d -> tentando update..." % st)
        st, body = _http("POST", "%s/api/v1/tools/id/%s/update" % (base, tool_id), token, form)

    ok = False
    if st == 200 and not _parece_html(body):
        try:
            j = json.loads(body)
            if isinstance(j, dict) and j.get("id"):
                print("OK: id=%s name=%s" % (j.get("id"), j.get("name")))
                ok = True
        except Exception:
            pass
    if not ok:
        print("HTTP %d | resposta: %s" % (st, body[:400]))
        print("NAO publicou. Copie a mensagem e me mostre.")
        sys.exit(2)

    print("")
    print("PRONTO. Tool publicada. Configure as Valves e acople ao motor.")


if __name__ == "__main__":
    main()
