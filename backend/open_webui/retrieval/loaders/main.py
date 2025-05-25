import requests
import logging
import ftfy
import sys

from langchain_community.document_loaders import (
    AzureAIDocumentIntelligenceLoader,
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
    YoutubeLoader,
)
from langchain_core.documents import Document


from open_webui.retrieval.loaders.external_document import ExternalDocumentLoader
from open_webui.retrieval.loaders.mistral import MistralLoader

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

# Import unstructured for default document processing
try:
    from unstructured.partition.auto import partition
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition = None

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
    "json",
]


class TikaLoader:
    def __init__(self, url, file_path, mime_type=None, extract_images=None):
        self.url = url
        self.file_path = file_path
        self.mime_type = mime_type

        self.extract_images = extract_images

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        if self.mime_type is not None:
            headers = {"Content-Type": self.mime_type}
        else:
            headers = {}

        if self.extract_images == True:
            headers["X-Tika-PDFextractInlineImages"] = "true"

        endpoint = self.url
        if not endpoint.endswith("/"):
            endpoint += "/"
        endpoint += "tika/text"

        r = requests.put(endpoint, data=data, headers=headers)

        if r.ok:
            raw_metadata = r.json()
            text = raw_metadata.get("X-TIKA:content", "<No text content found>").strip()

            if "Content-Type" in raw_metadata:
                headers["Content-Type"] = raw_metadata["Content-Type"]

            log.debug("Tika extracted text: %s", text)

            return [Document(page_content=text, metadata=headers)]
        else:
            raise Exception(f"Error calling Tika: {r.reason}")


class DoclingLoader:
    def __init__(self, url, file_path=None, mime_type=None, params=None):
        self.url = url.rstrip("/")
        self.file_path = file_path
        self.mime_type = mime_type

        self.params = params or {}

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            files = {
                "files": (
                    self.file_path,
                    f,
                    self.mime_type or "application/octet-stream",
                )
            }

            params = {
                "image_export_mode": "placeholder",
                "table_mode": "accurate",
            }

            if self.params:
                if self.params.get("do_picture_classification"):
                    params["do_picture_classification"] = self.params.get(
                        "do_picture_classification"
                    )

                if self.params.get("ocr_engine") and self.params.get("ocr_lang"):
                    params["ocr_engine"] = self.params.get("ocr_engine")
                    params["ocr_lang"] = [
                        lang.strip()
                        for lang in self.params.get("ocr_lang").split(",")
                        if lang.strip()
                    ]

            endpoint = f"{self.url}/v1alpha/convert/file"
            r = requests.post(endpoint, files=files, data=params)

        if r.ok:
            result = r.json()
            document_data = result.get("document", {})
            text = document_data.get("md_content", "<No text content found>")

            metadata = {"Content-Type": self.mime_type} if self.mime_type else {}

            log.debug("Docling extracted text: %s", text)

            return [Document(page_content=text, metadata=metadata)]
        else:
            error_msg = f"Error calling Docling API: {r.reason}"
            if r.text:
                try:
                    error_data = r.json()
                    if "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                except Exception:
                    error_msg += f" - {r.text}"
            raise Exception(f"Error calling Docling: {error_msg}")


class UnstructuredLoader:
    """
    Unstructured.io loader for comprehensive document processing.
    This is the DEFAULT loader when no specific engine is selected.
    """
    def __init__(self, file_path, extract_images=None):
        self.file_path = file_path
        self.extract_images = extract_images
        self.nltk_ready = self._ensure_nltk_data()

    def _ensure_nltk_data(self):
        """Ensure required NLTK data is available for Unstructured.io"""
        try:
            import nltk
            # Download required NLTK data if not already present
            nltk.download('punkt_tab', quiet=True)
            nltk.download('averaged_perceptron_tagger_eng', quiet=True)
            log.debug("NLTK data ensured for Unstructured.io")
            return True
        except Exception as e:
            log.warning(f"Could not download NLTK data during initialization: {e}")
            return False

    def load(self) -> list[Document]:
        if not UNSTRUCTURED_AVAILABLE:
            raise Exception(
                "Unstructured library not available. Install with: pip install unstructured[all-docs]"
            )
        
        try:
            # Retry NLTK data download if it failed during initialization
            if not self.nltk_ready:
                log.info("Retrying NLTK data download before processing...")
                self.nltk_ready = self._ensure_nltk_data()
            
            # Use unstructured.io's auto partition with minimal parameters to avoid conflicts
            elements = partition(filename=self.file_path)
            
            if not elements:
                log.warning("No elements extracted from document")
                return [Document(page_content="No content extracted", metadata={"source": self.file_path})]
            
            # Convert elements to documents
            docs = []
            for i, element in enumerate(elements):
                # Get text content
                text = str(element)
                if not text.strip():
                    continue
                
                # Create metadata
                metadata = {
                    "source": self.file_path,
                    "element_id": i,
                    "element_type": element.category if hasattr(element, 'category') else 'unknown',
                }
                
                # Add page number if available
                if hasattr(element, 'metadata') and element.metadata:
                    if hasattr(element.metadata, 'page_number'):
                        metadata["page"] = element.metadata.page_number
                    if hasattr(element.metadata, 'filename'):
                        metadata["filename"] = element.metadata.filename
                
                docs.append(Document(page_content=text, metadata=metadata))
            
            log.info(f"Unstructured.io extracted {len(docs)} document elements")
            return docs if docs else [Document(page_content="No content extracted", metadata={"source": self.file_path})]
            
        except Exception as e:
            error_msg = str(e)
            log.error(f"Error processing document with Unstructured.io: {error_msg}")
            
            # Provide specific guidance for common NLTK errors
            if "punkt_tab" in error_msg or "NLTK" in error_msg:
                detailed_error = (
                    f"Unstructured.io processing failed due to missing NLTK data: {error_msg}\n"
                    "To fix this issue, run the following commands:\n"
                    "1. pip install nltk\n"
                    "2. python -c \"import nltk; nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng')\""
                )
                raise Exception(detailed_error)
            
            # Re-raise the exception to force proper error handling
            raise Exception(f"Unstructured.io processing failed: {error_msg}")


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

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or (
            file_content_type and file_content_type.find("text/") >= 0
        )

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split(".")[-1].lower()

        if (
            self.engine == "external"
            and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL")
            and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY")
        ):
            loader = ExternalDocumentLoader(
                file_path=file_path,
                url=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL"),
                api_key=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY"),
                mime_type=file_content_type,
            )
        if self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TikaLoader(
                    url=self.kwargs.get("TIKA_SERVER_URL"),
                    file_path=file_path,
                    mime_type=file_content_type,
                    extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
                )
        elif self.engine == "docling" and self.kwargs.get("DOCLING_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = DoclingLoader(
                    url=self.kwargs.get("DOCLING_SERVER_URL"),
                    file_path=file_path,
                    mime_type=file_content_type,
                    params={
                        "ocr_engine": self.kwargs.get("DOCLING_OCR_ENGINE"),
                        "ocr_lang": self.kwargs.get("DOCLING_OCR_LANG"),
                        "do_picture_classification": self.kwargs.get(
                            "DOCLING_DO_PICTURE_DESCRIPTION"
                        ),
                    },
                )
        elif (
            self.engine == "document_intelligence"
            and self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT") != ""
            and self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY") != ""
            and (
                file_ext in ["pdf", "xls", "xlsx", "docx", "ppt", "pptx"]
                or file_content_type
                in [
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ]
            )
        ):
            loader = AzureAIDocumentIntelligenceLoader(
                file_path=file_path,
                api_endpoint=self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT"),
                api_key=self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY"),
            )
        elif (
            self.engine == "mistral_ocr"
            and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
            and file_ext
            in ["pdf"]  # Mistral OCR currently only supports PDF and images
        ):
            loader = MistralLoader(
                api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
            )
        elif (
            self.engine == "external"
            and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
            and file_ext
            in ["pdf"]  # Mistral OCR currently only supports PDF and images
        ):
            loader = MistralLoader(
                api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
            )
        else:
            # DEFAULT: Use Unstructured.io for comprehensive document processing
            # This handles ALL file types with intelligent processing
            log.info(f"Using DEFAULT Unstructured.io engine for file: {filename}")
            loader = UnstructuredLoader(
                file_path=file_path,
                extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
            )

        return loader
