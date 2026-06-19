"""Registro de extratores por formato (Fatia 2: apenas .docx).

O extrator .docx em si nao depende de outros modulos do open_webui (so stdlib +
lxml + python-docx), o que o torna testavel isoladamente. detect_format e puro.
"""

from open_webui.editorial.extractors.docx import extract_docx

# Mapa formato -> funcao extratora. .pdf/.epub/.odt entram nas fatias seguintes.
EXTRACTORS = {
    "docx": extract_docx,
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
