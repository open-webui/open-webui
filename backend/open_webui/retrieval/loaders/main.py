import requests
import logging
import ftfy
import sys
import json

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
from open_webui.retrieval.loaders.datalab_marker import DatalabMarkerLoader


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
        
        log.info("DoclingLoader initialized with URL: %s, file: %s, mime_type: %s", 
                self.url, self.file_path, self.mime_type)

    def load(self) -> list[Document]:
        log.info("Starting Docling document processing for file: %s", self.file_path)
        
        with open(self.file_path, "rb") as f:
            files = {
                "files": (
                    self.file_path,
                    f,
                    self.mime_type or "application/octet-stream",
                )
            }

            params = {"image_export_mode": "embedded", "table_mode": "fast", "to_formats": "md", "pdf_backend": "pypdfium2", "pipeline": "standard", "do_table_structure": True, "include_images": True}

            if self.params:
                log.debug("Processing custom parameters: %s", self.params)
                if self.params.get("do_picture_description"):
                    params["do_picture_description"] = self.params.get(
                        "do_picture_description"
                    )
                    log.debug("Picture description enabled: %s", 
                             self.params.get("do_picture_description"))

                    picture_description_mode = self.params.get(
                        "picture_description_mode", ""
                    ).lower()

                    if picture_description_mode == "local" and self.params.get(
                        "picture_description_local", {}
                    ):
                        params["picture_description_local"] = json.dumps(
                            self.params.get("picture_description_local", {})
                        )
                        log.debug("Using local picture description mode")

                    elif picture_description_mode == "api" and self.params.get(
                        "picture_description_api", {}
                    ):
                        params["picture_description_api"] = json.dumps(
                            self.params.get("picture_description_api", {})
                        )
                        log.debug("Using API picture description mode")

                if self.params.get("ocr_engine") and self.params.get("ocr_lang"):
                    params["ocr_engine"] = self.params.get("ocr_engine")
                    # Convert list to comma-separated string for API
                    ocr_langs = [
                        lang.strip()
                        for lang in self.params.get("ocr_lang").split(",")
                        if lang.strip()
                    ]
                    params["ocr_language"] = ",".join(ocr_langs)
                    log.debug("OCR settings - engine: %s, languages: %s", 
                             params["ocr_engine"], params["ocr_language"])


            endpoint = f"{self.url}/v1/convert/file"
            log.info("Making request to Docling endpoint: %s", endpoint)
            log.info("Request parameters: %s", params)
            
            r = requests.post(endpoint, files=files, data=params)

        if r.ok:
            log.info("Docling API request successful, status code: %d", r.status_code)
            result = r.json()
            
            # Check if this is an async task
            if "task_id" in result:
                task_id = result["task_id"]
                log.info("Received task ID: %s, starting polling for completion", task_id)
                return self._poll_task_result(task_id)
            
            # Direct result
            document_data = result.get("document", {})
            text = document_data.get("md_content", "<No text content found>")

            metadata = {"Content-Type": self.mime_type} if self.mime_type else {}

            log.info("Docling extracted text: %s", text)
            log.info("Successfully processed document, extracted %d characters", len(text))

            return [Document(page_content=text, metadata=metadata)]
        else:
            log.error("Docling API request failed with status code: %d", r.status_code)
            log.error("Response reason: %s", r.reason)
            if r.text:
                log.error("Response text: %s", r.text)
                
            error_msg = f"Error calling Docling API: {r.reason}"
            if r.text:
                try:
                    error_data = r.json()
                    if "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                        log.error("Error detail from API: %s", error_data['detail'])
                except Exception:
                    error_msg += f" - {r.text}"
                    log.error("Failed to parse error response as JSON")
            raise Exception(f"Error calling Docling: {error_msg}")

    def _poll_task_result(self, task_id: str) -> list[Document]:
        """Poll for task completion and return the result."""
        import time
        
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            log.info("Polling task %s, attempt %d/%d", task_id, attempt, max_attempts)
            
            # Wait before polling
            if attempt > 1:
                time.sleep(5)
            
            # Check task status
            status_endpoint = f"{self.url}/v1/tasks/{task_id}"
            try:
                r = requests.get(status_endpoint)
                
                if r.ok:
                    result = r.json()
                    status = result.get("status", "unknown")
                    log.info("Task %s status: %s", task_id, status)
                    
                    if status == "completed":
                        log.info("Task %s completed successfully", task_id)
                        document_data = result.get("document", {})
                        text = document_data.get("md_content", "<No text content found>")
                        
                        metadata = {"Content-Type": self.mime_type} if self.mime_type else {}
                        log.debug("Docling extracted text: %s", text)
                        log.info("Successfully processed document, extracted %d characters", len(text))
                        
                        return [Document(page_content=text, metadata=metadata)]
                    
                    elif status == "failed":
                        error_msg = result.get("error", "Unknown error")
                        log.error("Task %s failed: %s", task_id, error_msg)
                        raise Exception(f"Docling task failed: {error_msg}")
                    
                    elif status in ["pending", "processing"]:
                        log.info("Task %s still %s, continuing to poll", task_id, status)
                        continue
                    
                    else:
                        log.warning("Unknown task status: %s", status)
                        continue
                        
                else:
                    log.error("Failed to get task status, status code: %d", r.status_code)
                    if r.text:
                        log.error("Status response: %s", r.text)
                    
            except requests.RequestException as e:
                log.error("Request error while polling task %s: %s", task_id, str(e))
                if attempt == max_attempts:
                    raise Exception(f"Failed to poll task {task_id}: {str(e)}")
                continue
        
        # Timeout
        log.error("Task %s timed out after %d attempts", task_id, max_attempts)
        raise Exception(f"Docling task {task_id} timed out after {max_attempts} attempts")


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
        elif self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TikaLoader(
                    url=self.kwargs.get("TIKA_SERVER_URL"),
                    file_path=file_path,
                    mime_type=file_content_type,
                    extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
                )
        elif (
            self.engine == "datalab_marker"
            and self.kwargs.get("DATALAB_MARKER_API_KEY")
            and file_ext
            in [
                "pdf",
                "xls",
                "xlsx",
                "ods",
                "doc",
                "docx",
                "odt",
                "ppt",
                "pptx",
                "odp",
                "html",
                "epub",
                "png",
                "jpeg",
                "jpg",
                "webp",
                "gif",
                "tiff",
            ]
        ):
            loader = DatalabMarkerLoader(
                file_path=file_path,
                api_key=self.kwargs["DATALAB_MARKER_API_KEY"],
                langs=self.kwargs.get("DATALAB_MARKER_LANGS"),
                use_llm=self.kwargs.get("DATALAB_MARKER_USE_LLM", False),
                skip_cache=self.kwargs.get("DATALAB_MARKER_SKIP_CACHE", False),
                force_ocr=self.kwargs.get("DATALAB_MARKER_FORCE_OCR", False),
                paginate=self.kwargs.get("DATALAB_MARKER_PAGINATE", False),
                strip_existing_ocr=self.kwargs.get(
                    "DATALAB_MARKER_STRIP_EXISTING_OCR", False
                ),
                disable_image_extraction=self.kwargs.get(
                    "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION", False
                ),
                output_format=self.kwargs.get(
                    "DATALAB_MARKER_OUTPUT_FORMAT", "markdown"
                ),
            )
        elif self.engine == "docling" and self.kwargs.get("DOCLING_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                # Build params for DoclingLoader
                params = self.kwargs.get("DOCLING_PARAMS", {})
                if not isinstance(params, dict):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        log.error("Invalid DOCLING_PARAMS format, expected JSON object")
                        params = {}

                loader = DoclingLoader(
                    url=self.kwargs.get("DOCLING_SERVER_URL"),
                    file_path=file_path,
                    mime_type=file_content_type,
                    params=params,
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
