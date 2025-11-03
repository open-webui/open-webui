import requests
import logging
import ftfy
import sys

from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    ImageFormatOption,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, OcrAutoOptions

from langchain_community.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
)
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

known_source_ext = [
    "go",
    "py",
    "java",
    "sh",
    "bat",
    "ps1",
    "cmd",
    "js",
    "ts",
    "css",
    "cpp",
    "hpp",
    "h",
    "c",
    "cs",
    "sql",
    "log",
    "ini",
    "pl",
    "pm",
    "r",
    "dart",
    "dockerfile",
    "env",
    "php",
    "hs",
    "hsc",
    "lua",
    "nginxconf",
    "conf",
    "m",
    "mm",
    "plsql",
    "perl",
    "rb",
    "rs",
    "db2",
    "scala",
    "bash",
    "swift",
    "vue",
    "svelte",
    "msg",
    "ex",
    "exs",
    "erl",
    "tsx",
    "jsx",
    "hs",
    "lhs",
]


class TikaLoader:
    def __init__(self, url, file_path, mime_type=None):
        self.url = url
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        if self.mime_type is not None:
            headers = {"Content-Type": self.mime_type}
        else:
            headers = {}

        endpoint = self.url
        if not endpoint.endswith("/"):
            endpoint += "/"
        endpoint += "tika/text"

        r = requests.put(endpoint, data=data, headers=headers)

        if r.ok:
            raw_metadata = r.json()
            text = raw_metadata.get("X-TIKA:content", "<No text content found>")

            if "Content-Type" in raw_metadata:
                headers["Content-Type"] = raw_metadata["Content-Type"]

            log.debug("Tika extracted text: %s", text)

            return [Document(page_content=text, metadata=headers)]
        else:
            raise Exception(f"Error calling Tika: {r.reason}")


class DoclingLoader:
    """Advanced document loader using Docling for superior structure extraction."""

    def __init__(self, file_path: str, mime_type: str = None):
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        """Load and convert document using Docling with OCR fallback."""
        try:
            import os

            log.info(f"DoclingLoader processing: {self.file_path}")

            file_ext = os.path.splitext(self.file_path)[1].lower()
            format_options = self._get_format_options(file_ext)

            # Create converter and process document
            converter = (
                DocumentConverter(format_options=format_options)
                if format_options
                else DocumentConverter()
            )

            try:
                result = converter.convert(self.file_path)
                log.info("Document conversion successful")
            except Exception as e:
                result = self._handle_ocr_fallback(e, file_ext)

            return self._extract_documents(result, file_ext)

        except Exception as e:
            log.error(f"Error processing document with Docling: {str(e)}")
            raise Exception(f"Error processing document with Docling: {str(e)}")

    def _get_format_options(self, file_ext: str) -> dict:
        """Get format options only for files that need custom OCR configuration."""
        if file_ext == ".pdf":
            return self._get_pdf_options()
        elif file_ext in [
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".tif",
            ".bmp",
            ".gif",
            ".webp",
        ]:
            return self._get_image_options()
        return {}  # Use Docling defaults for everything else

    def _get_pdf_options(self) -> dict:
        """Conservative PDF options with minimal OCR."""
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = True
        pdf_options.do_table_structure = True
        pdf_options.ocr_options = OcrAutoOptions(
            force_full_page_ocr=False, bitmap_area_threshold=0.1
        )

        log.info("DoclingLoader: Using PDF pipeline with conservative OCR")
        return {InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}

    def _get_image_options(self) -> dict:
        """Minimal image options with essential OCR."""
        image_options = PdfPipelineOptions()
        image_options.do_ocr = True
        image_options.ocr_options = OcrAutoOptions(
            force_full_page_ocr=True, bitmap_area_threshold=0.01
        )

        log.info("DoclingLoader: Using Image pipeline with minimal OCR")
        return {InputFormat.IMAGE: ImageFormatOption(pipeline_options=image_options)}

    def _handle_ocr_fallback(self, error: Exception, file_ext: str):
        """Handle OCR failures with appropriate fallback strategies."""
        error_msg = str(error)

        if any(
            keyword in error_msg.lower()
            for keyword in ["font", "download", "modelscope", "rapidocr"]
        ):
            log.warning(f"OCR failed due to dependency issue: {error}")
            log.info("Attempting conversion with OCR disabled")

            if file_ext == ".pdf":
                return self._fallback_pdf_conversion()
            elif file_ext in [
                ".png",
                ".jpg",
                ".jpeg",
                ".tiff",
                ".tif",
                ".bmp",
                ".gif",
                ".webp",
            ]:
                raise Exception(
                    f"Image processing requires OCR, but OCR failed: {error}. Please check network connectivity."
                )
            else:
                return DocumentConverter().convert(self.file_path)
        else:
            raise error

    def _fallback_pdf_conversion(self):
        """Fallback PDF conversion without OCR."""
        fallback_options = PdfPipelineOptions()
        fallback_options.do_ocr = False
        fallback_options.do_table_structure = True

        fallback_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=fallback_options)
            }
        )

        result = fallback_converter.convert(self.file_path)
        log.info("Fallback conversion successful")
        return result

    def _extract_documents(self, result, file_ext: str) -> list[Document]:
        """Extract documents from conversion result."""
        documents = []
        if result and hasattr(result, "document"):
            markdown_content = result.document.export_to_markdown()

            metadata = {
                "source": self.file_path,
                "file_type": file_ext,
                "loader": "docling",
            }

            if hasattr(result.document, "pages"):
                metadata["page_count"] = len(result.document.pages)

            documents.append(Document(page_content=markdown_content, metadata=metadata))

            log.info(
                f"DoclingLoader successfully processed {len(documents)} document(s)"
            )

        return documents


class Loader:
    def __init__(self, engine: str = "", **kwargs):
        self.engine = engine
        self.kwargs = kwargs

    def load(
        self, filename: str, file_content_type: str, file_path: str
    ) -> list[Document]:
        loader = self._get_loader(filename, file_content_type, file_path)
        docs = loader.load()

        return [
            Document(
                page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
            )
            for doc in docs
        ]

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split(".")[-1].lower()

        if self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
            if file_ext in known_source_ext or (
                file_content_type and file_content_type.find("text/") >= 0
            ):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TikaLoader(
                    url=self.kwargs.get("TIKA_SERVER_URL"),
                    file_path=file_path,
                    mime_type=file_content_type,
                )
        elif self.engine == "docling":
            if file_ext in known_source_ext or (
                file_content_type and file_content_type.find("text/") >= 0
            ):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = DoclingLoader(
                    file_path=file_path,
                    mime_type=file_content_type,
                )
        else:
            if file_ext == "pdf":
                loader = PyPDFLoader(
                    file_path, extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
                )
            elif file_ext == "csv":
                loader = CSVLoader(file_path)
            elif file_ext == "rst":
                loader = UnstructuredRSTLoader(file_path, mode="elements")
            elif file_ext == "xml":
                loader = UnstructuredXMLLoader(file_path)
            elif file_ext in ["htm", "html"]:
                loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
            elif file_ext == "md":
                loader = TextLoader(file_path, autodetect_encoding=True)
            elif file_content_type == "application/epub+zip":
                loader = UnstructuredEPubLoader(file_path)
            elif (
                file_content_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                or file_ext == "docx"
            ):
                loader = Docx2txtLoader(file_path)
            elif file_content_type in [
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ] or file_ext in ["xls", "xlsx"]:
                loader = UnstructuredExcelLoader(file_path)
            elif file_content_type in [
                "application/vnd.ms-powerpoint",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ] or file_ext in ["ppt", "pptx"]:
                loader = UnstructuredPowerPointLoader(file_path)
            elif file_ext == "msg":
                loader = OutlookMessageLoader(file_path)
            elif file_ext in known_source_ext or (
                file_content_type and file_content_type.find("text/") >= 0
            ):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TextLoader(file_path, autodetect_encoding=True)

        return loader
