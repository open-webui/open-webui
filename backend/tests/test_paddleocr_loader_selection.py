from langchain_community.document_loaders import TextLoader
from open_webui.retrieval.loaders.main import Loader
from open_webui.retrieval.loaders.paddleocr_vl import PaddleOCRVLLoader


def test_paddleocr_vl_falls_back_to_text_loader_for_markdown(tmp_path):
    file_path = tmp_path / 'notes.md'
    file_path.write_text('# Notes\n\nPlain markdown should not be sent to OCR.', encoding='utf-8')

    loader = Loader(
        engine='paddleocr_vl',
        PADDLEOCR_VL_BASE_URL='http://paddleocr.example',
        PADDLEOCR_VL_TOKEN='token',
    )

    selected_loader = loader._get_loader('notes.md', 'text/markdown', str(file_path))

    assert isinstance(selected_loader, TextLoader)


def test_paddleocr_vl_handles_supported_pdf_files(tmp_path):
    file_path = tmp_path / 'paper.pdf'
    file_path.write_bytes(b'%PDF-1.4\n')

    loader = Loader(
        engine='paddleocr_vl',
        PADDLEOCR_VL_BASE_URL='http://paddleocr.example',
        PADDLEOCR_VL_TOKEN='token',
    )

    selected_loader = loader._get_loader('paper.pdf', 'application/pdf', str(file_path))

    assert isinstance(selected_loader, PaddleOCRVLLoader)
