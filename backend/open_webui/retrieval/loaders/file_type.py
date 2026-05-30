import zipfile


OOXML_FILE_TYPES = {
    'word/document.xml': 'docx',
    'xl/workbook.xml': 'xlsx',
    'ppt/presentation.xml': 'pptx',
}


def detect_ooxml_file_type(file_path: str) -> str | None:
    try:
        with zipfile.ZipFile(file_path) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return None

    for marker, file_type in OOXML_FILE_TYPES.items():
        if marker in names:
            return file_type
    return None
