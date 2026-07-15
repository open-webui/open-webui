"""
title: Relatorio de Ambientes Nidum
author: Nidum
version: 1.1.0
description: Gera o relatorio do motor Identificador de Ambientes no modelo visual aprovado (HTML/CSS -> PDF via WeasyPrint), com foto embutida, selos de severidade, barra de confianca e a identidade Nidum. Devolve link de download nativo. So-ASCII no codigo; o CONTEUDO do PDF tem acentuacao correta (rotulos fixos via entidades HTML; texto do modelo vem acentuado).
changelog:
  1.1.0:
    - Secao "Material analisado": coluna de qualidade reestruturada (rotulos + espacamento)
      para preencher melhor o espaco ao lado da foto. Novo campo "Dimensao estimada do
      objeto" (parametro dimensao_estimada).
  1.0.2:
    - Data carimbada pelo servidor (datetime.now) no campo DATA e na parte da data do
      nome do arquivo. O modelo nao decide mais a data (evita data inventada).
  1.0.1:
    - Remove o cabecalho 'requirements': weasyprint (62.3) e pillow (12.1.1) ja estao
      na imagem (backend/requirements.txt). Evita reinstalacao no load, que estourava o
      tempo de resposta ao publicar (IncompleteRead).
  1.0.0:
    - Primeira versao. Template derivado de Tec_Modelo_Visual_Relatorio_Ambientes_14072026_V1.
"""

import asyncio
import base64
import html as _html
import inspect
import io
import logging
import os
import re
import uuid
from datetime import datetime

from pydantic import BaseModel

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- assets
def _brand_dir():
    candidates = []
    try:
        import open_webui

        candidates.append(os.path.join(os.path.dirname(open_webui.__file__), "static", "brand"))
    except Exception:
        pass
    candidates.append("/app/backend/open_webui/static/brand")
    for d in candidates:
        if d and os.path.isdir(d):
            return d
    return None


def _font_path(fname):
    d = _brand_dir()
    if not d:
        return None
    p = os.path.join(d, "fonts", fname)
    return p if os.path.isfile(p) else None


def _logo_data_uri(cor="terracota"):
    d = _brand_dir()
    if not d:
        return ""
    p = os.path.join(d, "logos", "nidum-" + str(cor) + ".png")
    if not os.path.isfile(p):
        return ""
    try:
        return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode("ascii")
    except Exception:
        return ""


def _font_face(fname, family, weight, style="normal"):
    p = _font_path(fname)
    if not p:
        return ""
    try:
        b64 = base64.b64encode(open(p, "rb").read()).decode("ascii")
    except Exception:
        return ""
    return (
        "@font-face{font-family:'%s';font-weight:%s;font-style:%s;"
        "src:url(data:font/ttf;base64,%s) format('truetype');}" % (family, weight, style, b64)
    )


def _fontes_css():
    # Fontes da marca embutidas em base64 (PDF autocontido). Fallback: DejaVu do sistema.
    regras = [
        _font_face("MaximaNouva-Regular.ttf", "Maxima Nouva", 400),
        _font_face("MaximaNouva-SemiBold.ttf", "Maxima Nouva", 600),
        _font_face("MaximaNouva-Bold.ttf", "Maxima Nouva", 700),
        _font_face("MaximaNouva-Italic.ttf", "Maxima Nouva", 400, "italic"),
        _font_face("Ibrand.ttf", "Ibrand", 400),
    ]
    return "".join(r for r in regras if r)


# --------------------------------------------------------------------------- user/io
def _get_user_id(__user__):
    if __user__ is None:
        return None
    if isinstance(__user__, dict):
        return __user__.get("id")
    return getattr(__user__, "id", None)


async def _ler_bytes(file_id):
    # Le os bytes de um arquivo pelos modulos internos (Files + Storage). NUNCA HTTP.
    from open_webui.models.files import Files
    from open_webui.storage.provider import Storage

    f = Files.get_file_by_id(file_id)
    if inspect.isawaitable(f):
        f = await f
    if not f:
        return None, None
    path = getattr(f, "path", None)
    meta = getattr(f, "meta", None) or {}
    ctype = (meta.get("content_type") if isinstance(meta, dict) else None) or ""
    if not path:
        return None, ctype

    def _get():
        local = Storage.get_file(path)  # devolve caminho local (baixa se remoto)
        if isinstance(local, (bytes, bytearray)):
            return bytes(local)
        with open(local, "rb") as fh:
            return fh.read()

    try:
        return await asyncio.to_thread(_get), ctype
    except Exception as e:
        log.warning("relatorio_ambientes: falha ao ler file_id %s: %s", file_id, e)
        return None, ctype


def _img_data_uri(raw, max_w=1000):
    # Redimensiona proporcional (Pillow) e devolve data URI JPEG/PNG. Converte formatos
    # nao suportados. Em caso de erro, devolve "".
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.mode in ("RGBA", "P", "LA"):
            fundo = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            fundo.paste(im, mask=im.split()[-1])
            im = fundo
        else:
            im = im.convert("RGB")
        if im.width > max_w:
            h = int(im.height * (max_w / float(im.width)))
            im = im.resize((max_w, h), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        log.warning("relatorio_ambientes: falha ao processar imagem: %s", e)
        return ""


def _raw_de_data_uri(uri):
    # "data:image/...;base64,XXXX" -> bytes; devolve None se nao for data URI valida.
    try:
        if not isinstance(uri, str) or not uri.startswith("data:"):
            return None
        _cab, b64 = uri.split(",", 1)
        return base64.b64decode(b64)
    except Exception:
        return None


async def _coletar_fotos_do_contexto(messages, files, limite=4):
    # Coleta as imagens que o usuario enviou na conversa, SEM depender do modelo passar
    # file_id. Fontes: (1) arquivos anexados (__files__); (2) conteudo multimodal das
    # mensagens (__messages__, itens image_url com data URI). Devolve data URIs JPEG
    # ja processadas (Pillow), deduplicadas, na ordem de descoberta.
    brutos = []

    # 1) arquivos anexados a requisicao
    for f in (files or []):
        if not isinstance(f, dict):
            continue
        url = f.get("url")
        raw = _raw_de_data_uri(url) if isinstance(url, str) else None
        if raw:
            brutos.append(raw)
            continue
        fobj = f.get("file") if isinstance(f.get("file"), dict) else {}
        fid = f.get("id") or fobj.get("id")
        ctype = ((fobj.get("meta") or {}).get("content_type") or "") if fobj else ""
        tipo = (f.get("type") or "").lower()
        if fid and ("image" in tipo or str(ctype).startswith("image")):
            raw, _ct = await _ler_bytes(fid)
            if raw:
                brutos.append(raw)

    # 2) imagens embutidas nas mensagens (conteudo multimodal), da mais recente p/ a mais antiga
    for m in reversed(messages or []):
        if not isinstance(m, dict):
            continue
        cont = m.get("content")
        if isinstance(cont, list):
            for item in cont:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    url = (item.get("image_url") or {}).get("url")
                    raw = _raw_de_data_uri(url)
                    if raw:
                        brutos.append(raw)
        if len(brutos) >= limite:
            break

    uris, vistos = [], set()
    for raw in brutos:
        chave = (len(raw), raw[:24])
        if chave in vistos:
            continue
        vistos.add(chave)
        uri = _img_data_uri(raw)
        if uri:
            uris.append(uri)
        if len(uris) >= limite:
            break
    return uris


async def _salvar_e_linkar(data_bytes, filename, content_type, user_id):
    from open_webui.storage.provider import Storage
    from open_webui.models.files import Files, FileForm

    file_id = str(uuid.uuid4())
    stored_name = file_id + "_" + filename
    tags = {"OpenWebUI-User-Id": user_id} if user_id else {}

    def _upload():
        tentativas = []
        if tags:
            tentativas.append(lambda: Storage.upload_file(io.BytesIO(data_bytes), stored_name, tags))
        tentativas.append(lambda: Storage.upload_file(io.BytesIO(data_bytes), stored_name, {}))
        if tags:
            tentativas.append(lambda: Storage.upload_file(data_bytes, stored_name, tags))
        tentativas.append(lambda: Storage.upload_file(data_bytes, stored_name, {}))
        tentativas.append(lambda: Storage.upload_file(data_bytes, stored_name))
        last = None
        for tentar in tentativas:
            try:
                return tentar()
            except Exception as e:
                last = e
        raise RuntimeError("Falha ao salvar no Storage: " + str(last))

    result = await asyncio.to_thread(_upload)
    file_path = result[1] if isinstance(result, tuple) and len(result) >= 2 else result
    if not file_path:
        raise RuntimeError("Storage.upload_file devolveu caminho vazio.")

    meta = {"name": filename, "content_type": content_type, "size": len(data_bytes)}
    form = FileForm(id=file_id, filename=filename, path=file_path, meta=meta, data={})
    inserted = Files.insert_new_file(user_id, form)
    if inspect.isawaitable(inserted):
        inserted = await inserted
    if inserted is None:
        raise RuntimeError("Falha ao registrar o arquivo no banco (insert_new_file).")
    return "/api/v1/files/" + file_id + "/content"


# --------------------------------------------------------------------------- helpers HTML
def _e(txt):
    # Escapa < > & " (mantendo acentos) do conteudo dinamico vindo do modelo.
    return _html.escape(str(txt if txt is not None else ""), quote=True)


_SEV = {
    "BAIXA": ("baixa", "Baixa"),
    "MEDIA": ("media", "M&eacute;dia"),
    "ALTA": ("alta", "Alta"),
    "NC": ("nc", "N&atilde;o conf."),
}


def _selo(sev):
    cls, rot = _SEV.get(str(sev or "").strip().upper(), ("nc", "N&atilde;o conf."))
    return '<span class="sev %s">%s</span>' % (cls, rot)


# --------------------------------------------------------------------------- template
# ASCII no codigo; rotulos fixos com ENTIDADES HTML (viram acento no PDF).
TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><style>
[[FONTES]]
:root{--areia:#E5E0D5;--pedra:#9D9890;--ceu:#4F7187;--terracota:#9A4A2E;--musgo:#515E52;--escuro:#1F1E1B;--branco:#FFFFFF;}
@page{size:A4;margin:14mm 12mm;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--branco);color:var(--escuro);font-family:"Maxima Nouva","DejaVu Sans",Arial,sans-serif;font-size:12px;line-height:1.55;}
h1,h2{font-family:"Ibrand","Maxima Nouva","DejaVu Sans",Arial,sans-serif;line-height:1.2;}
.topo{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;}
.logo img{height:24px;}
.origem{text-align:right;font-size:9px;color:var(--pedra);letter-spacing:1px;text-transform:uppercase;line-height:1.6;}
h1{font-size:22px;color:var(--escuro);margin:14px 0 3px;font-weight:600;}
.subtitulo{color:var(--musgo);font-size:11px;margin-bottom:14px;}
.regua{height:3px;background:var(--terracota);}
.metadados{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--areia);border-top:none;margin-bottom:22px;}
.metadados div{padding:8px 10px;border-right:1px solid var(--areia);}
.metadados div:last-child{border-right:none;}
.metadados .rotulo{display:block;font-size:8px;letter-spacing:1px;text-transform:uppercase;color:var(--pedra);margin-bottom:2px;}
.metadados .valor{font-size:11px;font-weight:600;}
.sumario{display:grid;grid-template-columns:1fr 170px;gap:20px;background:#F5F2EB;padding:16px 18px;margin-bottom:26px;border-left:5px solid var(--terracota);}
.sumario .dl{font-size:13px;font-weight:600;line-height:1.45;}
.sumario .dl small{display:block;font-size:8px;letter-spacing:1px;font-weight:400;text-transform:uppercase;color:var(--pedra);margin-bottom:5px;}
.confianca{text-align:right;}
.confianca .num{font-family:"Ibrand","DejaVu Sans",Arial,sans-serif;font-size:34px;color:var(--ceu);line-height:1;}
.confianca .faixa{height:8px;background:var(--areia);border-radius:4px;margin:7px 0 5px;overflow:hidden;}
.confianca .faixa span{display:block;height:100%;background:var(--ceu);}
.confianca .leitura{font-size:9.5px;color:var(--musgo);line-height:1.4;}
section{margin-bottom:24px;}
h2{font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:var(--terracota);font-weight:700;padding-bottom:5px;border-bottom:1px solid var(--areia);margin-bottom:10px;}
p{margin-bottom:9px;}
.fotos{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap;}
.foto{width:270px;}
.foto img{width:100%;border:1px solid var(--pedra);}
.foto .semimg{width:100%;height:170px;background:var(--areia);display:flex;align-items:center;justify-content:center;color:var(--pedra);font-size:11px;border:1px solid var(--pedra);}
.foto figcaption{font-size:10px;color:var(--musgo);margin-top:5px;}
.qualidade{flex:1;min-width:220px;padding-top:2px;}
.qbloco{margin-bottom:18px;}
.qrot{display:block;font-size:8px;letter-spacing:1px;text-transform:uppercase;color:var(--pedra);margin-bottom:7px;}
.qval{font-size:14px;font-weight:600;color:var(--escuro);line-height:1.4;}
.qobs{font-size:9.5px;color:var(--pedra);margin-top:2px;}
.chips{display:flex;flex-wrap:wrap;gap:8px;}
.chip{font-size:10px;padding:4px 10px;border-radius:12px;background:#F5F2EB;border:1px solid var(--areia);color:var(--escuro);}
.chip b{color:var(--musgo);font-weight:700;}
.evidencias{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;margin-top:6px;}
.evidencia{font-size:11.5px;padding-left:13px;position:relative;}
.evidencia::before{content:"";position:absolute;left:0;top:6px;width:6px;height:6px;background:var(--ceu);}
table{width:100%;border-collapse:collapse;font-size:11.5px;}
th{text-align:left;font-size:8.5px;letter-spacing:1px;text-transform:uppercase;color:var(--pedra);padding:5px 8px;border-bottom:2px solid var(--areia);font-weight:700;}
td{padding:7px 8px;border-bottom:1px solid var(--areia);vertical-align:top;}
.sev{display:inline-block;font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#fff;padding:3px 9px;border-radius:3px;white-space:nowrap;}
.sev.baixa{background:var(--musgo);}
.sev.media{background:var(--ceu);}
.sev.alta{background:var(--terracota);}
.sev.nc{background:var(--pedra);}
.incerteza{background:#F5F2EB;padding:12px 16px;margin-top:10px;}
.incerteza .t{font-size:8.5px;letter-spacing:1px;text-transform:uppercase;color:var(--ceu);font-weight:700;margin-bottom:7px;}
.incerteza ol{margin-left:16px;font-size:11.5px;}
.incerteza li{margin-bottom:4px;}
.ressalva{border:1px solid var(--pedra);padding:12px 16px;font-size:11px;color:var(--musgo);margin-top:6px;}
.ressalva b{color:var(--escuro);}
.rodape{display:flex;justify-content:space-between;margin-top:28px;padding-top:12px;border-top:1px solid var(--areia);font-size:9.5px;color:var(--pedra);}
</style></head><body>
<div class="topo">
  <div class="logo">[[LOGO]]</div>
  <div class="origem">Identificador de Ambientes<br>ChatND &middot; Plataforma Nidum</div>
</div>
<h1>[[TITULO]]</h1>
<div class="subtitulo">An&aacute;lise visual assistida por IA &middot; car&aacute;ter orientativo</div>
<div class="regua"></div>
<div class="metadados">
  <div><span class="rotulo">Data da an&aacute;lise</span><span class="valor">[[DATA]]</span></div>
  <div><span class="rotulo">Autor</span><span class="valor">[[AUTOR]]</span></div>
  <div><span class="rotulo">Projeto / obra</span><span class="valor">[[PROJETO]]</span></div>
  <div><span class="rotulo">Documento</span><span class="valor">[[DOCUMENTO]]</span></div>
</div>
<div class="sumario">
  <div class="dl"><small>Diagn&oacute;stico</small>[[DIAG_RESUMO]]</div>
  <div class="confianca">
    <div class="num">[[CONF_PCT]]%</div>
    <div class="faixa"><span style="width:[[CONF_PCT]]%"></span></div>
    <div class="leitura">[[CONF_LEITURA]]</div>
  </div>
</div>
<section>
  <h2>Material analisado</h2>
  <div class="fotos">
    [[FOTOS]]
    <div class="qualidade">
      <div class="qbloco">
        <span class="qrot">Qualidade da imagem</span>
        <div class="chips">[[CHIPS]]</div>
      </div>
      <div class="qbloco">
        <span class="qrot">Dimens&atilde;o estimada do objeto</span>
        <div class="qval">[[DIMENSAO]]</div>
      </div>
      <p class="qobs">[[QTD_FOTOS]]</p>
    </div>
  </div>
</section>
<section>
  <h2>Diagn&oacute;stico e evid&ecirc;ncias</h2>
  <p>[[DIAG_TEXTO]]</p>
  <div class="evidencias">[[EVIDENCIAS]]</div>
</section>
<section>
  <h2>Avarias e estado de conserva&ccedil;&atilde;o</h2>
  <table>
    <tr><th style="width:32%">Avaria</th><th style="width:26%">Localiza&ccedil;&atilde;o</th><th style="width:14%">Severidade</th><th>Observa&ccedil;&atilde;o</th></tr>
    [[AVARIAS]]
  </table>
</section>
<section>
  <h2>Grau de confian&ccedil;a</h2>
  <p>[[CONF_TEXTO]]</p>
  <div class="incerteza"><div class="t">O que reduziria a incerteza</div><ol>[[REDUZIR]]</ol></div>
</section>
<section>
  <h2>Ajustes da conversa</h2>
  <p>[[AJUSTES]]</p>
</section>
<div class="ressalva"><b>Ressalva.</b> Esta an&aacute;lise visual assistida por IA tem car&aacute;ter orientativo e n&atilde;o substitui vistoria t&eacute;cnica presencial em decis&otilde;es estruturais, jur&iacute;dicas ou de alto valor.</div>
<div class="rodape"><span>nidum &mdash; fazer da casa um ninho.</span><span>[[DOCUMENTO]] &middot; p&aacute;gina 1</span></div>
</body></html>
"""


class Tools:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def gerar_relatorio_ambientes(
        self,
        titulo_humano: str,
        nome_arquivo: str,
        metadados: dict,
        diagnostico_resumo: str,
        confianca: dict,
        qualidade_imagem: dict,
        diagnostico_texto: str,
        evidencias: list,
        avarias: list,
        confianca_texto: str,
        reduzir_incerteza: list,
        ajustes_conversa: str = "Nenhum ajuste registrado nesta conversa",
        dimensao_estimada: str = "Nao estimavel sem referencia de escala",
        fotos: list = None,
        __user__: dict = None,
        __messages__: list = None,
        __files__: list = None,
    ) -> str:
        """Gera o relatorio do Identificador de Ambientes no modelo visual aprovado (PDF) e devolve o link de download.

        :param titulo_humano: titulo legivel do documento. Ex.: "Relatorio de Analise - Piso Ceramico".
        :param nome_arquivo: nome tecnico no padrao PLAT_Relatorio_<Elemento>_<DDMMAAAA>_V<n> (sem extensao, sem campos vazios).
        :param metadados: dict com data, autor, projeto (use "Nao informado" quando faltar).
        :param diagnostico_resumo: uma frase para o sumario executivo.
        :param confianca: dict com percentual (int 0-100) e leitura (frase curta).
        :param qualidade_imagem: dict com nitidez, iluminacao, angulo, referencia_escala.
        :param diagnostico_texto: prosa completa do diagnostico.
        :param evidencias: lista de itens curtos (strings) para a grade de evidencias.
        :param avarias: lista de dicts: avaria, localizacao, severidade (BAIXA|MEDIA|ALTA|NC), observacao.
        :param confianca_texto: justificativa completa do grau de confianca.
        :param reduzir_incerteza: lista de itens (strings) numerados.
        :param ajustes_conversa: correcoes/adicoes do usuario, ou "Nenhum ajuste registrado nesta conversa".
        :param dimensao_estimada: dimensao estimada do objeto/material (ex.: "aprox. 60 x 40 cm"
            ou "Nao estimavel sem referencia de escala" quando a foto nao permite).
        :param fotos: OPCIONAL. Lista de dicts com 'legenda' (as imagens sao coletadas
            automaticamente da conversa; nao e preciso informar file_id).
        :return: link /api/v1/files/{id}/content para baixar o PDF.
        """
        try:
            return await self._gerar(
                titulo_humano, nome_arquivo, metadados, diagnostico_resumo, confianca,
                qualidade_imagem, diagnostico_texto, evidencias, avarias, confianca_texto,
                reduzir_incerteza, ajustes_conversa, dimensao_estimada, fotos, __user__,
                __messages__, __files__,
            )
        except Exception as e:
            log.error("relatorio_ambientes: erro: %s", e)
            return ("Nao consegui gerar o relatorio agora. Tente novamente; se persistir, "
                    "avise o suporte. (detalhe tecnico registrado no log)")

    async def _gerar(self, titulo, nome_arquivo, meta, diag_resumo, conf, qual, diag_texto,
                     evidencias, avarias, conf_texto, reduzir, ajustes, dimensao, fotos, __user__,
                     __messages__=None, __files__=None):
        import weasyprint

        meta = dict(meta or {})
        conf = conf or {}
        qual = qual or {}
        fotos = fotos or []

        # data: carimbada pelo SERVIDOR (o modelo nao decide a data - evita data inventada).
        agora = datetime.now()
        data_br = agora.strftime("%d/%m/%Y")
        data_arq = agora.strftime("%d%m%Y")
        meta["data"] = data_br

        # nome do arquivo: garante padrao minimo e sem underscore solto no final
        nome = str(nome_arquivo or "").strip().rstrip("_").strip()
        if not nome:
            nome = "PLAT_Relatorio"
        if nome.lower().endswith(".pdf"):
            nome = nome[:-4]
        # normaliza a data no nome (troca uma sequencia de 8 digitos pela data real;
        # se nao houver, insere antes do _V<n> ou no fim)
        if re.search(r"\d{8}", nome):
            nome = re.sub(r"\d{8}", data_arq, nome, count=1)
        else:
            m = re.search(r"(_[vV]\d+)$", nome)
            if m:
                nome = nome[:m.start()] + "_" + data_arq + m.group(1)
            else:
                nome = nome + "_" + data_arq
        nome_pdf = nome + ".pdf"

        try:
            pct = int(round(float(conf.get("percentual", 0))))
        except Exception:
            pct = 0
        pct = max(0, min(100, pct))

        # fotos embutidas (max 4): coletadas automaticamente da conversa (nao dependem do
        # modelo passar file_id). Legendas do modelo (se houver) sao aplicadas em ordem.
        user_id = _get_user_id(__user__)
        legendas = [(f or {}).get("legenda") for f in fotos if isinstance(f, dict)]
        uris = await _coletar_fotos_do_contexto(__messages__, __files__, limite=4)
        # fallback: modelo passou file_id explicito e nada foi coletado do contexto
        if not uris and fotos:
            for f in fotos[:4]:
                fid = (f or {}).get("file_id")
                if fid:
                    raw, _ct = await _ler_bytes(fid)
                    if raw:
                        u = _img_data_uri(raw)
                        if u:
                            uris.append(u)
        blocos_foto = []
        for i, uri in enumerate(uris[:4], start=1):
            leg = legendas[i - 1] if (i - 1) < len(legendas) and legendas[i - 1] else ("Foto %d" % i)
            img = '<img src="%s" alt="Foto %d">' % (uri, i)
            blocos_foto.append('<figure class="foto">%s<figcaption>%s</figcaption></figure>' % (img, _e(leg)))
        fotos_html = "".join(blocos_foto) if blocos_foto else '<figure class="foto"><div class="semimg">[ sem foto ]</div></figure>'
        qtd = len(uris)
        qtd_txt = _e("%d foto(s) recebida(s)." % qtd)

        # chips de qualidade
        def chip(rot, val):
            return '<span class="chip">%s: <b>%s</b></span>' % (rot, _e(val or "nao avaliado"))
        chips = "".join([
            chip("Nitidez", qual.get("nitidez")),
            chip("Ilumina&ccedil;&atilde;o", qual.get("iluminacao")),
            chip("&Acirc;ngulo", qual.get("angulo")),
            chip("Refer&ecirc;ncia de escala", qual.get("referencia_escala")),
        ])

        evid_html = "".join('<div class="evidencia">%s</div>' % _e(x) for x in (evidencias or [])) \
            or '<div class="evidencia">Sem evid&ecirc;ncias registradas.</div>'

        linhas = []
        for a in (avarias or []):
            a = a or {}
            linhas.append(
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    _e(a.get("avaria")), _e(a.get("localizacao")),
                    _selo(a.get("severidade")), _e(a.get("observacao")))
            )
        avarias_html = "".join(linhas) or '<tr><td colspan="4">Nenhuma avaria registrada.</td></tr>'

        reduzir_html = "".join("<li>%s</li>" % _e(x) for x in (reduzir or [])) \
            or "<li>Sem itens registrados.</li>"

        subs = {
            "[[FONTES]]": _fontes_css(),
            "[[LOGO]]": ('<img src="%s" alt="nidum">' % _logo_data_uri("terracota")) if _logo_data_uri("terracota") else "nidum",
            "[[TITULO]]": _e(titulo or "Relatorio de Analise"),
            "[[DATA]]": _e(meta.get("data") or "Nao informado"),
            "[[AUTOR]]": _e(meta.get("autor") or "Nao informado"),
            "[[PROJETO]]": _e(meta.get("projeto") or "Nao informado"),
            "[[DOCUMENTO]]": _e(nome),
            "[[DIAG_RESUMO]]": _e(diag_resumo),
            "[[CONF_PCT]]": str(pct),
            "[[CONF_LEITURA]]": _e(conf.get("leitura") or ""),
            "[[FOTOS]]": fotos_html,
            "[[QTD_FOTOS]]": qtd_txt,
            "[[CHIPS]]": chips,
            "[[DIMENSAO]]": _e(dimensao or "Nao estimavel sem referencia de escala"),
            "[[DIAG_TEXTO]]": _e(diag_texto),
            "[[EVIDENCIAS]]": evid_html,
            "[[AVARIAS]]": avarias_html,
            "[[CONF_TEXTO]]": _e(conf_texto),
            "[[REDUZIR]]": reduzir_html,
            "[[AJUSTES]]": _e(ajustes or "Nenhum ajuste registrado nesta conversa"),
        }
        html_doc = TEMPLATE
        for k, v in subs.items():
            html_doc = html_doc.replace(k, v)

        pdf_bytes = await asyncio.to_thread(lambda: weasyprint.HTML(string=html_doc).write_pdf())
        link = await _salvar_e_linkar(pdf_bytes, nome_pdf, "application/pdf", user_id)
        return "Relatorio gerado: [%s](%s)" % (nome_pdf, link)
