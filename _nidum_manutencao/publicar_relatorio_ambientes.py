# -*- coding: ascii -*-
"""
Publica (ou atualiza) a tool 'relatorio_ambientes_nidum' na imagem VIVA do ChatND.

Le o arquivo _nidum_tools/relatorio_ambientes_nidum.py deste repositorio e envia
para a API do Open WebUI. Ao carregar, o Open WebUI instala o 'requirements:'
(weasyprint, pillow) do cabecalho da tool.

COMO USAR (no seu terminal):
  1) defina as duas variaveis de ambiente:
       PowerShell:
         $env:NIDUM_URL   = "https://SEU-APP.up.railway.app"
         $env:NIDUM_TOKEN = "SEU_TOKEN_ADMIN"
     (o token admin sai de: ChatND -> foto -> Configuracoes -> Conta -> chave de API)
  2) rode:
         python _nidum_manutencao/publicar_relatorio_ambientes.py

Se a tool ja existir, o script atualiza (nao duplica).
So-ASCII (regra do projeto).
"""

import json
import os
import sys
import urllib.request
import urllib.error

TOOL_ID = "relatorio_ambientes_nidum"
TOOL_NAME = "Relatorio de Ambientes (modelo visual)"
TOOL_DESC = ("Gera o relatorio de identificacao de ambientes no modelo visual "
             "aprovado (WeasyPrint) e devolve o link para download.")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_PATH = os.path.join(HERE, "..", "_nidum_tools", "relatorio_ambientes_nidum.py")


def _http(method, url, token, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e)


def _parece_html(txt):
    t = (txt or "").lstrip().lower()
    return t.startswith("<!doctype") or t.startswith("<html")


def main():
    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    if not base or not token:
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN antes de rodar. Veja o topo do arquivo.")
        sys.exit(1)

    # checagem previa: a URL aponta mesmo para o ChatND (Open WebUI)?
    print("Conferindo a URL: %s" % base)
    st0, body0 = _http("GET", "%s/api/config" % base, token)
    if _parece_html(body0) or st0 != 200:
        print("")
        print("ERRO: essa URL NAO respondeu como o ChatND (recebi HTTP %d%s)." % (
            st0, ", pagina HTML da Railway" if _parece_html(body0) else ""))
        print("A NIDUM_URL deve ser o MESMO endereco que voce abre no navegador para usar")
        print("o ChatND (a barra de endereco), sem barra no final. Ex.: https://chatnd-xxxx.up.railway.app")
        print("Ajuste e rode de novo:")
        print('  $env:NIDUM_URL = "https://ENDERECO-REAL-DO-CHATND"')
        sys.exit(1)
    print("URL confere (ChatND respondeu).")

    with open(CODE_PATH, "r", encoding="ascii") as fh:
        content = fh.read()
    print("Codigo lido: %d bytes de %s" % (len(content), os.path.normpath(CODE_PATH)))

    form = {"id": TOOL_ID, "name": TOOL_NAME, "content": content,
            "meta": {"description": TOOL_DESC}}

    # tenta criar; se ja existe, atualiza
    print("Publicando (create)... isso instala weasyprint/pillow e pode levar ~1 min.")
    st, body = _http("POST", "%s/api/v1/tools/create" % base, token, form)
    if st == 200:
        print("OK: tool criada.")
    elif st == 400 and "already" in body.lower() or (st == 400 and "existe" in body.lower()):
        print("Ja existe -> atualizando (update)...")
        st2, body2 = _http("POST", "%s/api/v1/tools/id/%s/update" % (base, TOOL_ID), token, form)
        st, body = st2, body2
        print("OK: tool atualizada." if st2 == 200 else "Falha no update.")
    # se o create falhou por ja existir mas a mensagem for outra, tenta update mesmo assim
    if st != 200:
        print("Create retornou HTTP %d. Tentando update como fallback..." % st)
        st, body = _http("POST", "%s/api/v1/tools/id/%s/update" % (base, TOOL_ID), token, form)

    print("HTTP %d" % st)
    ok = False
    if st == 200 and not _parece_html(body):
        try:
            j = json.loads(body)
            if isinstance(j, dict) and j.get("id"):
                print("Resposta: id=%s name=%s" % (j.get("id"), j.get("name")))
                ok = True
        except Exception:
            pass
    if not ok:
        print("Resposta (bruta): %s" % body[:400])

    if ok:
        print("")
        print("PRONTO. Tool publicada de verdade. Agora acople ao motor no proximo passo.")
    else:
        print("")
        print("NAO publicou (resposta nao era a API do ChatND). Copie a mensagem e me mostre.")
        sys.exit(2)


if __name__ == "__main__":
    main()
