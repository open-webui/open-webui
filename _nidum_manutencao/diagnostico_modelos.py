# -*- coding: ascii -*-
"""
Diagnostico SO-LEITURA dos modelos do ChatND (nao altera nada).

Mostra, para o modelo-base 'claude-opus-4-8' e para o motor
'nidum-identificador-ambientes':
  - se tem REGISTRO de modelo (info) e se e 'preset' (modelo cru de conexao);
  - o base_model_id;
  - o access (grants) configurado;
  - se esta ativo.

Serve para confirmar POR QUE da "Model not found" e qual a correcao certa.

USO:
  cd "C:\\Users\\daviv\\dev\\nidum-platform"
  $env:NIDUM_URL="https://chatnd.nidumbrasil.com.br"; $env:NIDUM_TOKEN="SEU_TOKEN_ADMIN"
  py _nidum_manutencao/diagnostico_modelos.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

ALVOS = ("claude-opus-4-8", "nidum-identificador-ambientes")


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


def _achar(models, alvo):
    for m in models:
        if str(m.get("id")) == alvo:
            return m
    # match parcial (caso o id tenha sufixo)
    for m in models:
        if alvo in str(m.get("id")):
            return m
    return None


def _resumo(m):
    if not m:
        return "  NAO ENCONTRADO na lista de modelos."
    info = m.get("info")
    tem_registro = bool(info)
    preset = m.get("preset")
    owned = m.get("owned_by")
    base = (info or {}).get("base_model_id") if info else m.get("base_model_id")
    ativo = (info or {}).get("is_active") if info else None
    grants = []
    if info:
        grants = info.get("access_grants") or (info.get("meta") or {}).get("access_grants") or []
    linhas = [
        "  id: %s" % m.get("id"),
        "  tem REGISTRO de modelo (info): %s" % ("SIM" if tem_registro else "NAO (modelo cru de conexao)"),
        "  preset (cru de conexao): %s" % preset,
        "  owned_by: %s" % owned,
        "  base_model_id: %s" % base,
        "  is_active: %s" % ativo,
        "  access_grants: %s" % (json.dumps(grants, ensure_ascii=True) if grants else "(vazio/privado)"),
    ]
    return "\n".join(linhas)


def main():
    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    if not base or not token:
        print("ERRO: defina NIDUM_URL e NIDUM_TOKEN. Veja o topo do arquivo.")
        sys.exit(1)

    st, body = _get("%s/api/v1/models" % base, token)
    if st != 200:
        print("Falha ao listar modelos (HTTP %d): %s" % (st, body[:300]))
        sys.exit(1)
    try:
        data = json.loads(body)
        models = data.get("data") if isinstance(data, dict) else data
        if not isinstance(models, list):
            models = data.get("models") if isinstance(data, dict) else []
    except Exception as e:
        print("Resposta nao-JSON:", body[:300])
        sys.exit(1)

    print("Total de modelos vistos pelo admin: %d\n" % len(models))
    for alvo in ALVOS:
        print("=== %s ===" % alvo)
        print(_resumo(_achar(models, alvo)))
        print("")

    print("Leitura: se 'claude-opus-4-8' tiver REGISTRO=SIM com access_grants que NAO")
    print("incluem o grupo, e isso que bloqueia o motor (Model not found). Removendo o")
    print("registro, ele vira 'modelo cru' -> motor funciona e ele some do seletor dos")
    print("usuarios comuns (so admin ve). Me mostre este resultado.")


if __name__ == "__main__":
    main()
