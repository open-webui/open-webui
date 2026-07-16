# -*- coding: ascii -*-
"""
Concede a permissao de ESCRITA (write) ao app 'chat ND - SharePoint' no site
tecnologia, via Microsoft Graph, autenticando VOCE (admin) por 'device code'
(login no navegador com um codigo curto). Nao instala nada; nao cola URL gigante.

Faz o PATCH direto (urllib), do mesmo jeito que a esteira ja faz chamadas ao Graph.
Nao contem segredo: SITE_ID e PERMISSION_ID sao identificadores publicos; o login e
seu, feito no navegador.

COMO USAR:
  cd "C:\\Users\\daviv\\dev\\nidum-platform"
  py _nidum_manutencao\\liberar_escrita_sharepoint.py

O script vai mostrar uma URL e um codigo. Abra a URL, entre com sua conta ADMIN e
digite o codigo. Depois ele libera a escrita e mostra o resultado.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Cliente publico oficial "Microsoft Graph Command Line Tools" (suporta device code).
CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPE = "https://graph.microsoft.com/Sites.FullControl.All offline_access openid profile"

GRAPH = "https://graph.microsoft.com/v1.0"
SITE_ID = ("nidumoficial.sharepoint.com,"
           "2c2acf59-d219-4f31-ab38-0fc02fb9cecf,"
           "05e47dfb-98ef-4a95-a712-19b5cca55f66")
PERMISSION_ID = ("aTowaS50fG1zLnNwLmV4dHw4NWI5OTQ3Ny1jZjJkLTQ3ZjktOGVjNS1kNTIyMTY0NDdi"
                 "NDJAM2U2MGM2YTItNDhhYy00MjA2LTk2NWQtOTk2ZDBhN2M1NjIx")


def _post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def iniciar_device_code():
    st, j = _post_form(AUTHORITY + "/oauth2/v2.0/devicecode",
                       {"client_id": CLIENT_ID, "scope": SCOPE})
    if st != 200 or "device_code" not in j:
        print("Falha ao iniciar o login:", j)
        sys.exit(1)
    print("")
    print("==================== FACA O LOGIN COMO ADMIN ====================")
    print(j.get("message", "Abra https://microsoft.com/devicelogin e digite o codigo."))
    print("================================================================")
    print("(aguardando voce concluir o login no navegador...)")
    return j


def esperar_token(dc):
    url = AUTHORITY + "/oauth2/v2.0/token"
    intervalo = int(dc.get("interval", 5))
    limite = time.time() + int(dc.get("expires_in", 900))
    while time.time() < limite:
        time.sleep(intervalo)
        st, j = _post_form(url, {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": CLIENT_ID,
            "device_code": dc["device_code"],
        })
        if st == 200 and "access_token" in j:
            return j["access_token"]
        err = j.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            intervalo += 5
            continue
        print("Falha no login:", j.get("error_description", j))
        sys.exit(1)
    print("Tempo esgotado. Rode de novo e conclua o login mais rapido.")
    sys.exit(1)


def conceder_escrita(token):
    url = "%s/sites/%s/permissions/%s" % (GRAPH, SITE_ID, PERMISSION_ID)
    body = json.dumps({"roles": ["write"]}).encode()
    req = urllib.request.Request(
        url, data=body, method="PATCH",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    dc = iniciar_device_code()
    token = esperar_token(dc)
    st, body = conceder_escrita(token)
    print("")
    print("PATCH ->", st)
    try:
        j = json.loads(body)
        print("roles agora:", j.get("roles"))
    except Exception:
        print(body[:500])
    if st == 200:
        print("")
        print("OK! Escrita liberada para o app no site. Volte ao ChatND, rode o")
        print("diagnostico (deve dar Escrita: OK) e mande salvar o relatorio.")
    else:
        print("")
        print("Nao funcionou. Copie o resultado acima e me mostre.")
        sys.exit(2)


if __name__ == "__main__":
    main()
