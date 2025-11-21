import requests
import logging
import ftfy
import sys
import json

from azure.identity import DefaultAzureCredential
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
    UnstructuredODTLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
    YoutubeLoader,
)
from langchain_core.documents import Document

from open_webui.retrieval.loaders.external_document import ExternalDocumentLoader

from open_webui.retrieval.loaders.mistral import MistralLoader
from open_webui.retrieval.loaders.datalab_marker import DatalabMarkerLoader
from open_webui.retrieval.loaders.mineru import MinerULoader


from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


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

            params = {"image_export_mode": "placeholder"}

            if self.params:
                if self.params.get("do_picture_description"):
                    params["do_picture_description"] = self.params.get(
                        "do_picture_description"
                    )

                    picture_description_mode = self.params.get(
                        "picture_description_mode", ""
                    ).lower()

                    if picture_description_mode == "local" and self.params.get(
                        "picture_description_local", {}
                    ):
                        params["picture_description_local"] = json.dumps(
                            self.params.get("picture_description_local", {})
                        )

                    elif picture_description_mode == "api" and self.params.get(
                        "picture_description_api", {}
                    ):
                        params["picture_description_api"] = json.dumps(
                            self.params.get("picture_description_api", {})
                        )

                params["do_ocr"] = self.params.get("do_ocr")

                params["force_ocr"] = self.params.get("force_ocr")

                if (
                    self.params.get("do_ocr")
                    and self.params.get("ocr_engine")
                    and self.params.get("ocr_lang")
                ):
                    params["ocr_engine"] = self.params.get("ocr_engine")
                    params["ocr_lang"] = [
                        lang.strip()
                        for lang in self.params.get("ocr_lang").split(",")
                        if lang.strip()
                    ]

                if self.params.get("pdf_backend"):
                    params["pdf_backend"] = self.params.get("pdf_backend")

                if self.params.get("table_mode"):
                    params["table_mode"] = self.params.get("table_mode")

                if self.params.get("pipeline"):
                    params["pipeline"] = self.params.get("pipeline")

            endpoint = f"{self.url}/v1/convert/file"
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
        self.user = kwargs.get("user", None)
        self.kwargs = kwargs

    def load(
        self, filename: str, file_content_type: str, file_path: str
    ) -> list[Document] | tuple[list[Document], list[str]]:
        loader = self._get_loader(filename, file_content_type, file_path)
        raw_result = loader.load()

        # NEW: preserve image_refs if present
        if isinstance(raw_result, tuple) and len(raw_result) == 2:
            docs, image_refs = raw_result
        else:
            docs = raw_result
            image_refs = None

        from collections.abc import Iterable
        from langchain_core.documents import Document as LCDocument

        flat_docs: list[LCDocument] = []

        def _flatten(items):
            for item in items:
                # Avoid treating strings/bytes/Documents as generic iterables
                if isinstance(item, Iterable) and not isinstance(
                    item, (str, bytes, LCDocument)
                ):
                    yield from _flatten(item)
                else:
                    yield item

        for item in _flatten(docs):
            if isinstance(item, LCDocument):
                flat_docs.append(
                    Document(
                        page_content=ftfy.fix_text(item.page_content),
                        metadata=item.metadata,
                    )
                )
            else:
                log.warning(
                    "Loader returned non-Document item of type %s; skipping: %r",
                    type(item),
                    item,
                )

        # NEW: return tuple if we originally had image_refs
        if image_refs is not None:
            return flat_docs, image_refs

        return flat_docs

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or (
            file_content_type
            and file_content_type.find("text/") >= 0
            # Avoid text/html files being detected as text
            and not file_content_type.find("html") >= 0
        )

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        # ... existing _get_loader implementation remains unchanged ...
        file_ext = filename.split(".")[-1].lower()

        if self.engine == "youtube":
            loader = YoutubeLoader.from_youtube_url(
                file_path, add_video_info=True, language="en"
            )
        elif self.engine == "web":
            loader = ExternalDocumentLoader(
                url=self.kwargs.get("WEB_LOADER_URL"),
                file_path=file_path,
                mime_type=file_content_type,
                extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
            )
        elif self.engine == "azure_document_intelligence":
            credential = DefaultAzureCredential()
            loader = AzureAIDocumentIntelligenceLoader(
                api_key=self.kwargs.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY"),
                api_endpoint=self.kwargs.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
                api_model=self.kwargs.get("AZURE_DOCUMENT_INTELLIGENCE_MODEL"),
                file_path=file_path,
                api_version=self.kwargs.get("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION"),
                mode="markdown",
                credential=credential,
                content_type=file_content_type,
            )
        elif self.engine == "tika":
            loader = TikaLoader(
                url=self.kwargs.get("TIKA_URL"),
                file_path=file_path,
                mime_type=file_content_type,
                extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
            )
        elif self.engine == "docling":
            loader = DoclingLoader(
                url=self.kwargs.get("DOCLING_URL"),
                file_path=file_path,
                mime_type=file_content_type,
                params=self.kwargs.get("DOCLING_PARAMS"),
            )
        elif self.engine == "mistral":
            loader = MistralLoader(
                file_path=file_path,
                MISTRAL_API_KEY=self.kwargs.get("MISTRAL_API_KEY"),
                MISTRAL_MODEL=self.kwargs.get("MISTRAL_FILE_PROCESSOR_MODEL"),
                params=self.kwargs.get("MISTRAL_FILE_PROCESSOR_PARAMS"),
            )
        elif self.engine == "datalab_marker":
            loader = DatalabMarkerLoader(
                file_path=file_path,
                DATALAB_MARKER_API_KEY=self.kwargs.get("DATALAB_MARKER_API_KEY"),
                DATALAB_MARKER_API_BASE_URL=self.kwargs.get(
                    "DATALAB_MARKER_API_BASE_URL"
                ),
                params=self.kwargs.get("DATALAB_MARKER_PARAMS"),
            )
        elif self.engine == "mineru":
            loader = MinerULoader(
                file_path=file_path,
                api_mode=self.kwargs.get("MINERU_API_MODE"),
                LOCAL_API_URL=self.kwargs.get("MINERU_LOCAL_API_URL"),
                CLOUD_API_URL=self.kwargs.get("MINERU_CLOUD_API_URL"),
                MINERU_API_KEY=self.kwargs.get("MINERU_API_KEY"),
                MINERU_PARAMS=self.kwargs.get("MINERU_PARAMS"),
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
            elif file_ext == "odt":
                loader = UnstructuredODTLoader(file_path)
            elif self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TextLoader(file_path, autodetect_encoding=True)

        return loader


known_source_ext = {
    "bat",
    "cmd",
    "cfg",
    "cfm",
    "cgi",
    "conf",
    "config",
    "cpp",
    "cs",
    "css",
    "csv",
    "env",
    "go",
    "h",
    "hpp",
    "hs",
    "html",
    "ini",
    "java",
    "js",
    "json",
    "kt",
    "kts",
    "lisp",
    "lua",
    "md",
    "php",
    "pl",
    "ps1",
    "py",
    "r",
    "rb",
    "rs",
    "scala",
    "sh",
    "sql",
    "ts",
    "tsx",
    "toml",
    "tsv",
    "txt",
    "vb",
    "vue",
    "xml",
    "yaml",
    "yml",
}