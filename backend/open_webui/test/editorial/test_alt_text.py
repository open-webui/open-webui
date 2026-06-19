"""Testes da F2.4a - extracao de imagens (.docx) + alt-text injetavel. Sem Redis."""

import base64
import io
import zipfile

from open_webui.editorial.alt_text import ensure_alt_text
from open_webui.editorial.extractors.docx import extract_docx

# PNG 1x1 transparente (valido).
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>"""

_DOCXML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Capitulo 1</w:t></w:r></w:p>
<w:p><w:r><w:drawing>
<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<wp:docPr id="1" name="Imagem 1" descr="Foto de um ninho de joao-de-barro"/>
<a:graphic><a:graphicData><a:blip r:embed="rId5"/></a:graphicData></a:graphic>
</wp:inline>
</w:drawing></w:r></w:p>
<w:p><w:r><w:drawing>
<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<wp:docPr id="2" name="Imagem 2"/>
<a:graphic><a:graphicData><a:blip r:embed="rId5"/></a:graphicData></a:graphic>
</wp:inline>
</w:drawing></w:r></w:p>
</w:body></w:document>"""


def _build_docx_with_image() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", _DOCXML)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/media/image1.png", _PNG)
    return buf.getvalue()


def test_docx_extracts_image_blocks_with_alt_and_bytes():
    tree = extract_docx(_build_docx_with_image())
    imgs = [b for b in tree["blocks"] if b["type"] == "image"]
    assert len(imgs) == 2

    # 1a imagem tem alt vindo do proprio documento (descr)
    assert imgs[0]["image"]["alt"] == "Foto de um ninho de joao-de-barro"
    assert imgs[0]["image"]["mime"] == "image/png"
    assert base64.b64decode(imgs[0]["image"]["b64"]) == _PNG

    # 2a imagem nao tem alt no documento
    assert imgs[1]["image"]["alt"] is None


async def test_ensure_alt_text_fills_only_missing():
    tree = extract_docx(_build_docx_with_image())

    calls = []

    async def fake_vision(data, mime):
        calls.append(mime)
        return "imagem gerada: um ninho"

    await ensure_alt_text(tree, vision=fake_vision)
    imgs = [b for b in tree["blocks"] if b["type"] == "image"]
    # nao sobrescreve a que ja tinha alt
    assert imgs[0]["image"]["alt"] == "Foto de um ninho de joao-de-barro"
    # preenche a que faltava
    assert imgs[1]["image"]["alt"] == "imagem gerada: um ninho"
    assert len(calls) == 1  # so chamou a visao para a imagem sem alt


async def test_ensure_alt_text_noop_without_vision():
    tree = extract_docx(_build_docx_with_image())
    await ensure_alt_text(tree, vision=None)
    imgs = [b for b in tree["blocks"] if b["type"] == "image"]
    assert imgs[1]["image"]["alt"] is None  # sem provedor, nao inventa


async def test_sync_vision_also_works():
    tree = extract_docx(_build_docx_with_image())

    def sync_vision(data, mime):
        return "alt sincrono"

    await ensure_alt_text(tree, vision=sync_vision)
    imgs = [b for b in tree["blocks"] if b["type"] == "image"]
    assert imgs[1]["image"]["alt"] == "alt sincrono"
