"""
title: SharePoint Nidum
author: Nidum
version: 1.0.2
description: Salva um arquivo ja gerado no ChatND (ex.: o relatorio do Identificador de Ambientes) numa pasta do SharePoint da Nidum, via Microsoft Graph (app-only). Nunca sobrescreve: se ja existir, incrementa a versao. Devolve o link do SharePoint. Segredos SOMENTE nas Valves (visiveis so por admin). So-ASCII no codigo.
changelog:
  1.0.2:
    - Adiciona diagnostico_sharepoint(): checa Valves/auth/biblioteca/escrita sem revelar
      segredos. Ajuda a distinguir Valves vazias de falta de permissao de escrita.
  1.0.1:
    - Pasta destino padrao: 4 - Pastas de Trabalho/Plataformas/ChatND Identificacao
      (fora do escopo da esteira). Cria apenas a subpasta que faltar.
  1.0.0:
    - Primeira versao. Reaproveita o app Entra ID da esteira (client credentials).
      Upload simples via PUT .../content (PDFs pequenos). Cria a pasta destino se faltar.
"""

# NOTA DE SEGURANCA: as credenciais (TENANT/CLIENT/SECRET) ficam nas Valves desta
# ferramenta, que so o administrador ve/edita. Nunca coloque segredo no codigo, no
# system prompt, nem em log. Esta ferramenta NAO revela segredos em nenhuma resposta.

import asyncio
import inspect
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"
LIMITE_PUT_SIMPLES = 200 * 1024 * 1024   # PUT .../content suporta ate ~250MB; guarda folgada


# --------------------------------------------------------------------------- io ChatND
def _get_user_id(__user__):
    if __user__ is None:
        return None
    if isinstance(__user__, dict):
        return __user__.get("id")
    return getattr(__user__, "id", None)


def _extrair_file_id(referencia):
    # Aceita um file_id puro OU um link /api/v1/files/<id>/content e devolve o id.
    txt = str(referencia or "").strip()
    m = re.search(r"files/([0-9a-fA-F-]{8,})", txt)
    if m:
        return m.group(1)
    return txt


async def _ler_arquivo(file_id):
    # Le (bytes, nome, content_type) de um arquivo do ChatND via modulos internos. NUNCA HTTP.
    from open_webui.models.files import Files
    from open_webui.storage.provider import Storage

    f = Files.get_file_by_id(file_id)
    if inspect.isawaitable(f):
        f = await f
    if not f:
        return None, None, None
    path = getattr(f, "path", None)
    meta = getattr(f, "meta", None) or {}
    if isinstance(meta, dict):
        ctype = meta.get("content_type") or "application/octet-stream"
        nome = meta.get("name")
    else:
        ctype = "application/octet-stream"
        nome = None
    nome = nome or getattr(f, "filename", None) or (str(file_id) + ".pdf")
    if not path:
        return None, nome, ctype

    def _get():
        local = Storage.get_file(path)
        if isinstance(local, (bytes, bytearray)):
            return bytes(local)
        with open(local, "rb") as fh:
            return fh.read()

    try:
        return await asyncio.to_thread(_get), nome, ctype
    except Exception as e:
        log.warning("sharepoint_nidum: falha ao ler file_id %s: %s", file_id, e)
        return None, nome, ctype


# --------------------------------------------------------------------------- Graph HTTP
def _req(method, url, headers=None, data=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _erro_http(e):
    try:
        corpo = e.read().decode("utf-8", "replace")
    except Exception:
        corpo = ""
    # nunca vaza segredo: so status + trecho curto da mensagem do Graph
    return "%s %s" % (getattr(e, "code", "?"), corpo[:300])


def _token(v):
    faltando = [n for n in ("TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "SITE_ID")
                if not str(getattr(v, n, "") or "").strip()]
    if faltando:
        raise RuntimeError("Configuracao incompleta (Valves): faltam " + ", ".join(faltando))
    url = "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % v.TENANT_ID.strip()
    data = urllib.parse.urlencode({
        "client_id": v.CLIENT_ID.strip(),
        "client_secret": v.CLIENT_SECRET.strip(),
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    try:
        _s, body = _req("POST", url, {"Content-Type": "application/x-www-form-urlencoded"}, data)
        return json.loads(body.decode())["access_token"]   # NUNCA imprimir/logar
    except urllib.error.HTTPError as e:
        raise RuntimeError("Falha de autenticacao no Microsoft Graph (app-only): " + _erro_http(e))


def _headers(token, extra=None):
    h = {"Authorization": "Bearer " + token}
    if extra:
        h.update(extra)
    return h


def _resolver_drive_id(token, site_id, biblioteca):
    url = "%s/sites/%s/drives?$select=id,name" % (GRAPH, urllib.parse.quote(site_id, safe=""))
    _s, body = _req("GET", url, _headers(token))
    drives = json.loads(body.decode("utf-8", "replace")).get("value", [])
    alvo = (biblioteca or "").strip().lower()
    for d in drives:
        if str(d.get("name", "")).strip().lower() == alvo:
            return d.get("id")
    nomes = ", ".join(repr(d.get("name")) for d in drives) or "(nenhuma)"
    raise RuntimeError("Biblioteca %r nao encontrada no site. Existentes: %s" % (biblioteca, nomes))


def _q_path(*segmentos):
    # monta segmentos de caminho para o endereco root:/... do Graph, com encoding seguro.
    partes = []
    for seg in segmentos:
        for pedaco in str(seg or "").strip("/").split("/"):
            if pedaco:
                partes.append(urllib.parse.quote(pedaco, safe=""))
    return "/".join(partes)


def _garantir_pasta(token, drive_id, pasta_destino):
    # Cria a pasta (e pais, se houver "/") caso nao exista. Idempotente.
    segmentos = [p for p in str(pasta_destino or "").strip("/").split("/") if p]
    caminho_pai = ""  # relativo a raiz do drive
    for nome in segmentos:
        if caminho_pai:
            url_pai = "%s/drives/%s/root:/%s:/children" % (GRAPH, drive_id, _q_path(caminho_pai))
        else:
            url_pai = "%s/drives/%s/root/children" % (GRAPH, drive_id)
        corpo = json.dumps({
            "name": nome,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        }).encode()
        try:
            _req("POST", url_pai, _headers(token, {"Content-Type": "application/json"}), corpo)
        except urllib.error.HTTPError as e:
            # 409 = ja existe -> ok; outros erros propagam
            if getattr(e, "code", None) != 409:
                raise RuntimeError("Falha ao criar/garantir a pasta %r: %s" % (nome, _erro_http(e)))
        caminho_pai = (caminho_pai + "/" + nome) if caminho_pai else nome


def _existe(token, drive_id, pasta_destino, nome_arquivo):
    url = "%s/drives/%s/root:/%s/%s" % (GRAPH, drive_id, _q_path(pasta_destino), _q_path(nome_arquivo))
    try:
        _req("GET", url + "?$select=id", _headers(token))
        return True
    except urllib.error.HTTPError as e:
        if getattr(e, "code", None) == 404:
            return False
        raise RuntimeError("Falha ao checar existencia de %r: %s" % (nome_arquivo, _erro_http(e)))


def _bump_versao(nome):
    # PLAT_..._V1.pdf -> _V2.pdf ; sem versao -> acrescenta _V2
    base = nome[:-4] if nome.lower().endswith(".pdf") else nome
    ext = ".pdf"
    m = re.search(r"_[vV](\d+)$", base)
    if m:
        base = base[:m.start()] + "_V" + str(int(m.group(1)) + 1)
    else:
        base = base + "_V2"
    return base + ext


def _nome_livre(token, drive_id, pasta_destino, nome_arquivo):
    nome = nome_arquivo
    for _ in range(200):
        if not _existe(token, drive_id, pasta_destino, nome):
            return nome
        nome = _bump_versao(nome)
    raise RuntimeError("Nao encontrei um nome livre para %r (muitas versoes)." % nome_arquivo)


def _upload(token, drive_id, pasta_destino, nome_arquivo, dados, content_type):
    url = "%s/drives/%s/root:/%s/%s:/content" % (
        GRAPH, drive_id, _q_path(pasta_destino), _q_path(nome_arquivo))
    headers = _headers(token, {"Content-Type": content_type or "application/octet-stream"})
    try:
        _s, body = _req("PUT", url, headers, dados)
        return json.loads(body.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("Falha ao enviar o arquivo ao SharePoint: " + _erro_http(e))


class Tools:
    class Valves(BaseModel):
        TENANT_ID: str = Field(
            default="", description="Directory (tenant) ID do app Entra ID. Segredo - so admin.")
        CLIENT_ID: str = Field(
            default="", description="Application (client) ID do app Entra ID. Segredo - so admin.")
        CLIENT_SECRET: str = Field(
            default="", description="Client secret do app Entra ID. Segredo - so admin. Nunca compartilhar.")
        SITE_ID: str = Field(
            default="", description="ID do site do SharePoint (o mesmo usado pela esteira).")
        BIBLIOTECA: str = Field(
            default="Nidum", description="Nome da biblioteca de documentos no site.")
        PASTA_DESTINO: str = Field(
            default="4 - Pastas de Trabalho/Plataformas/ChatND Identificacao",
            description="Pasta de destino (fora do escopo da esteira). Subpastas separadas por '/'. "
                        "So a pasta que faltar e criada; as existentes sao reaproveitadas.")

    def __init__(self):
        self.valves = self.Valves()

    async def diagnostico_sharepoint(self, __user__: dict = None) -> str:
        """Verifica a conexao com o SharePoint e diz exatamente onde falha, SEM revelar segredos.

        Use quando o arquivamento falhar. Checa: Valves preenchidas? token (autenticacao)?
        biblioteca encontrada? permissao de ESCRITA (tenta criar/garantir a pasta destino)?
        """
        v = self.valves
        linhas = []
        for n in ("TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "SITE_ID", "BIBLIOTECA", "PASTA_DESTINO"):
            val = str(getattr(v, n, "") or "").strip()
            linhas.append("- %s: %s" % (n, "preenchido" if val else "VAZIO"))
        cab = "Configuracao (Valves):\n" + "\n".join(linhas)

        try:
            token = await asyncio.to_thread(_token, v)
        except Exception as e:
            return cab + "\n\nAutenticacao: FALHOU\n  %s" % str(e)[:300]

        try:
            drive_id = await asyncio.to_thread(_resolver_drive_id, token, v.SITE_ID.strip(), v.BIBLIOTECA)
        except Exception as e:
            return cab + "\n\nAutenticacao: OK\nBiblioteca %r: NAO ENCONTRADA\n  %s" % (v.BIBLIOTECA, str(e)[:300])

        try:
            await asyncio.to_thread(_garantir_pasta, token, drive_id, v.PASTA_DESTINO)
            escrita = "OK (consegui criar/garantir a pasta destino)"
        except Exception as e:
            escrita = "FALHOU (provavel falta de permissao de ESCRITA do app no site)\n  %s" % str(e)[:300]
        return cab + "\n\nAutenticacao: OK\nBiblioteca: OK\nEscrita: %s" % escrita

    async def salvar_relatorio(
        self,
        arquivo: str,
        nome_arquivo: str = None,
        __user__: dict = None,
    ) -> str:
        """Salva no SharePoint um arquivo ja gerado no ChatND (ex.: o PDF do relatorio).

        Chame esta ferramenta SOMENTE depois de o usuario confirmar que quer salvar.
        Nunca sobrescreve: se ja existir um arquivo com o mesmo nome, salva como nova versao.

        :param arquivo: id do arquivo no ChatND OU o link /api/v1/files/<id>/content devolvido
            ao gerar o relatorio.
        :param nome_arquivo: nome final no SharePoint (com ou sem .pdf). Se vazio, usa o nome
            original do arquivo.
        :return: mensagem com o link do arquivo no SharePoint.
        """
        try:
            v = self.valves
            file_id = _extrair_file_id(arquivo)
            if not file_id:
                return "Nao recebi qual arquivo salvar. Gere o relatorio primeiro e tente de novo."

            dados, nome_orig, ctype = await _ler_arquivo(file_id)
            if not dados:
                return ("Nao consegui ler o arquivo do relatorio (id %s). Gere novamente e tente "
                        "de novo." % file_id)
            if len(dados) > LIMITE_PUT_SIMPLES:
                return "O arquivo e grande demais para o envio simples. Avise o suporte."

            nome = (nome_arquivo or nome_orig or "relatorio.pdf").strip()
            if not nome.lower().endswith(".pdf") and (ctype or "").lower() == "application/pdf":
                nome = nome + ".pdf"

            token = _token(v)
            drive_id = _resolver_drive_id(token, v.SITE_ID.strip(), v.BIBLIOTECA)
            _garantir_pasta(token, drive_id, v.PASTA_DESTINO)
            nome_final = _nome_livre(token, drive_id, v.PASTA_DESTINO, nome)
            item = _upload(token, drive_id, v.PASTA_DESTINO, nome_final, dados, ctype)

            link = item.get("webUrl") or ""
            versionado = " (salvo como nova versao para nao sobrescrever)" if nome_final != nome else ""
            if link:
                return ("Relatorio salvo no SharePoint em '%s/%s' como '%s'%s.\nLink: %s"
                        % (v.BIBLIOTECA, v.PASTA_DESTINO, nome_final, versionado, link))
            return ("Relatorio salvo no SharePoint em '%s/%s' como '%s'%s."
                    % (v.BIBLIOTECA, v.PASTA_DESTINO, nome_final, versionado))
        except Exception as e:
            log.error("sharepoint_nidum: erro: %s", e)
            return ("Nao consegui salvar no SharePoint agora. Detalhe: %s. Se persistir, avise o "
                    "suporte (pode ser permissao de escrita do aplicativo)." % str(e)[:300])
