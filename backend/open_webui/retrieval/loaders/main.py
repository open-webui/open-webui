import requests
import logging
import ftfy
import sys
import inspect

from typing import get_type_hints, Callable, List, Dict, Optional

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

from open_webui.retrieval.loaders.mistral import MistralLoader
from open_webui.models.functions import Functions, FunctionModel
from open_webui.utils.plugin import load_function_module_by_id

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
    def __init__(
        self, url, file_path=None, mime_type=None, ocr_engine=None, ocr_lang=None
    ):
        self.url = url.rstrip("/")
        self.file_path = file_path
        self.mime_type = mime_type
        self.ocr_engine = ocr_engine
        self.ocr_lang = ocr_lang

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

            if self.ocr_engine and self.ocr_lang:
                params["ocr_engine"] = self.ocr_engine
                params["ocr_lang"] = [
                    lang.strip() for lang in self.ocr_lang.split(",") if lang.strip()
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


class Loader:
    def __init__(self, engine: str = "", **kwargs):
        self.engine = engine
        self.kwargs = kwargs

    def load(
        self, filename: str, file_content_type: str, file_path: str
    ) -> list[Document]:
        loader = self._get_loader(filename, file_content_type, file_path)
        docs = loader.load()

        docs = self._run_document_processors(
            filename, file_content_type, file_path, docs
        )

        return [
            Document(
                page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
            )
            for doc in docs
        ]

    def _get_sorted_document_processors(self) -> List[FunctionModel]:
        def _get_priority(function_id) -> int:
            function = Functions.get_function_by_id(function_id)
            if function is not None:
                valves = Functions.get_function_valves_by_id(function_id)
                return valves.get("priority", 0) if valves else 0
            return 0

        docproc = Functions.get_functions_by_type("documentprocessor", active_only=True)
        docproc.sort(key=lambda f: _get_priority(f.id))
        return docproc

    def _load_valid_process_function(
        self, dp: Document, loaded_modules: Dict[str, object]
    ) -> Optional[Callable]:
        docp_id = dp.id
        docp_name = dp.name or docp_id

        try:
            if docp_id not in loaded_modules:
                loaded_modules[docp_id] = load_function_module_by_id(docp_id)

            function_module, _, _ = loaded_modules[docp_id]
            handler = getattr(function_module, "process", None)

            if not callable(handler):
                raise TypeError("process is not callable")

            sig = inspect.signature(handler)
            hints = get_type_hints(handler)

            if (
                len(sig.parameters) != 4
                or "doc" not in sig.parameters
                or hints.get("doc") != Document
                or "filename" not in sig.parameters
                or hints.get("filename") != str
                or "file_content_type" not in sig.parameters
                or hints.get("file_content_type") != str
                or "file_path" not in sig.parameters
                or hints.get("file_path") != str
            ):
                raise TypeError("Invalid process function signature")

            return handler
        except Exception as e:
            log.warning(f"Processor '{docp_name}' skipped: {e}")
            return None

    def _apply_processor_to_documents(
        self,
        handler: Callable,
        name: str,
        filename: str,
        file_content_type: str,
        file_path: str,
        docs: list[Document],
    ) -> None:
        for doc in docs:
            try:
                doc = handler(filename, file_content_type, file_path, doc)
            except Exception as e:
                log.warning(
                    f"Error in processor '{name}': {e}. "
                    f"Metadata: {doc.metadata}, "
                    f"Content (truncated): {doc.page_content[:200]}..."
                )

    def _run_document_processors(
        self,
        filename: str,
        file_content_type: str,
        file_path: str,
        docs: list[Document],
    ) -> list[Document]:
        docproc = self._get_sorted_document_processors()
        log.info(
            f"Loader {len(docproc)} active document processors found: {', '.join(dp.name or dp.id for dp in docproc)}"
        )
        loaded_modules: Dict[str, object] = {}

        for dp in docproc:
            handler = self._load_valid_process_function(dp, loaded_modules)
            if not handler:
                continue
            self._apply_processor_to_documents(
                handler, dp.name or dp.id, filename, file_content_type, file_path, docs
            )

        return docs

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or (
            file_content_type and file_content_type.find("text/") >= 0
        )

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split(".")[-1].lower()

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
                    ocr_engine=self.kwargs.get("DOCLING_OCR_ENGINE"),
                    ocr_lang=self.kwargs.get("DOCLING_OCR_LANG"),
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
        else:
            if file_ext == "pdf":
                loader = PyPDFLoader(
                    file_path, extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
                )
            elif file_ext == "csv":
                loader = CSVLoader(file_path, autodetect_encoding=True)
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
            elif self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TextLoader(file_path, autodetect_encoding=True)

        return loader
