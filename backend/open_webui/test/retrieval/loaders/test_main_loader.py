import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from open_webui.retrieval.loaders.file_type import detect_ooxml_file_type


def test_detects_word_ooxml_file_with_legacy_doc_extension(tmp_path):
    file_path = tmp_path / 'legacy.doc'
    with zipfile.ZipFile(file_path, 'w') as archive:
        archive.writestr('[Content_Types].xml', '')
        archive.writestr('word/document.xml', '<w:document />')

    assert detect_ooxml_file_type(str(file_path)) == 'docx'


def test_ignores_non_zip_files(tmp_path):
    file_path = tmp_path / 'legacy.doc'
    file_path.write_bytes(b'not a zip file')

    assert detect_ooxml_file_type(str(file_path)) is None
