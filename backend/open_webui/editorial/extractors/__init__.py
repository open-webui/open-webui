"""Registro de extratores por formato (Fatia 2: apenas .docx).

O extrator .docx em si nao depende de outros modulos do open_webui (so stdlib +
lxml + python-docx), o que o torna testavel isoladamente. detect_format e puro.
"""

from open_webui.editorial.extractors.docx import extract_docx
from open_webui.editorial.extractors.epub import extract_epub
from open_webui.editorial.extractors.odt import extract_odt
from open_webui.editorial.extractors.pdf import extract_pdf

# Mapa formato -> funcao extratora. As libs pesadas (pdfplumber, python-docx,
# bs4) sao importadas DENTRO de cada extrator, entao importar este modulo e leve.
EXTRACTORS = {
    "docx": extract_docx,
    "pdf": extract_pdf,
    "epub": extract_epub,
    "odt": extract_odt,
}


def detect_format(filename: str = None, fmt: str = None):
    """Descobre o formato a partir do campo 'format' (se vier) ou da extensao."""
    if fmt:
        return fmt.lower().lstrip(".")
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return None


def get_extractor(fmt: str):
    return EXTRACTORS.get(fmt)
