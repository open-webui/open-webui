"""Testes do export .epub (Fatia F2.2).

Estruturais sempre; a validacao FORMAL com EPUBCheck roda quando EPUBCHECK_JAR
estiver definido (no CI, com Java instalado).
"""

import io
import os
import re
import subprocess
import zipfile

import pytest
from lxml import etree

from open_webui.editorial.export.epub_export import build_epub
from open_webui.editorial.extractors.docx import extract_docx
from open_webui.test.editorial.test_docx_extractor import build_docx_with_footnote


def _epub_bytes():
    return build_epub(extract_docx(build_docx_with_footnote()))


def test_epub_mimetype_first_stored_and_wellformed():
    data = _epub_bytes()
    zf = zipfile.ZipFile(io.BytesIO(data))
    info0 = zf.infolist()[0]
    assert info0.filename == "mimetype"
    assert info0.compress_type == zipfile.ZIP_STORED
    assert zf.read("mimetype") == b"application/epub+zip"
    for n in zf.namelist():
        if n.endswith((".xml", ".xhtml", ".opf")):
            etree.fromstring(zf.read(n))  # lanca se malformado
    opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert "dcterms:modified" in opf
    assert 'properties="nav"' in opf


def test_epub_footnote_anchor_links_to_aside():
    zf = zipfile.ZipFile(io.BytesIO(_epub_bytes()))
    chap = zf.read("OEBPS/chap1.xhtml").decode("utf-8")
    assert 'epub:type="noteref"' in chap
    assert 'epub:type="footnote"' in chap
    ref = re.search(r'href="#([^"]+)"', chap).group(1)
    assert f'id="{ref}"' in chap


@pytest.mark.skipif(
    not os.environ.get("EPUBCHECK_JAR"),
    reason="EPUBCHECK_JAR nao definido (validacao formal roda no CI)",
)
def test_epub_passes_epubcheck(tmp_path):
    out = tmp_path / "out.epub"
    out.write_bytes(_epub_bytes())
    jar = os.environ["EPUBCHECK_JAR"]
    r = subprocess.run(
        ["java", "-jar", jar, str(out)], capture_output=True, text=True
    )
    assert r.returncode == 0, f"EPUBCheck falhou:\n{r.stdout}\n{r.stderr}"
