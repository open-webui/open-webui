import os
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


class Loader:
    def __init__(self, engine: str = "", **kwargs):
        self.engine = engine
        self.kwargs = kwargs

    def load(
        self, filename: str, file_content_type: str, file_path: str
    ) -> list[Document]:
        if not os.path.exists(file_path):
            log.error(f"[LOADER] FAILED | file={filename} | reason=FILE_NOT_FOUND | path={file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        log.info(f"[LOADER] START | file={filename} | size={file_size}B | engine={self.engine}")
        
        try:
            loader = self._get_loader(filename, file_content_type, file_path)
            log.info(f"[LOADER] CREATED | type={type(loader).__name__}")
            
            # DEBUG: Add detailed logging before calling loader.load()
            import time
            load_start = time.time()
            print(f"[DEBUG] About to call loader.load() | filename={filename} | loader_type={type(loader).__name__} | timestamp={load_start:.3f}", flush=True)
            log.info(f"[DEBUG] About to call loader.load() | filename={filename} | loader_type={type(loader).__name__} | timestamp={load_start:.3f}")
            
            # Check if it's PyPDFLoader and log extract_images value
            if isinstance(loader, PyPDFLoader):
                extract_images_val = getattr(loader, 'extract_images', 'unknown')
                print(f"[DEBUG] PyPDFLoader detected | extract_images={extract_images_val}", flush=True)
                log.info(f"[DEBUG] PyPDFLoader detected | extract_images={extract_images_val}")
            
            docs = loader.load()
            
            load_end = time.time()
            load_duration = load_end - load_start
            print(f"[DEBUG] loader.load() completed | filename={filename} | docs_count={len(docs) if docs else 0} | duration={load_duration:.2f}s | timestamp={load_end:.3f}", flush=True)
            log.info(f"[DEBUG] loader.load() completed | filename={filename} | docs_count={len(docs) if docs else 0} | duration={load_duration:.2f}s")
            total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
            non_empty = sum(1 for doc in docs if doc.page_content and doc.page_content.strip()) if docs else 0
            
            if len(docs) > 0:
                log.info(f"[LOADER] SUCCESS | file={filename} | docs={len(docs)} | chars={total_chars} | non_empty={non_empty}")
                if total_chars == 0:
                    log.error(f"[LOADER] WARNING | file={filename} | all docs have empty page_content")
            else:
                log.error(f"[LOADER] FAILED | file={filename} | reason=NO_DOCS_RETURNED")
        except Exception as e:
            log.error(f"[LOADER] FAILED | file={filename} | error={type(e).__name__}: {str(e)}", exc_info=True)
            raise

        result = [
            Document(
                page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
            )
            for doc in docs
        ]
        log.info(f"[Loader.load] Returning {len(result)} processed document(s)")
        return result

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        # FORCE PyPDF for PDFs (OpenShift requirement) - check PDF first before engine logic
        if file_ext == "pdf":
            # CRITICAL: Force extract_images=False to prevent hangs (image extraction causes 2+ minute slowdowns)
            extract_images = False
            log.info(f"[LOADER] PDF_DETECTED | file={filename} | loader=PyPDFLoader (forced) | extract_images={extract_images} (FORCED TO FALSE)")
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                log.info(f"[LOADER] PDF_INFO | file={filename} | size={file_size}B")
            print(f"[DEBUG] Creating PyPDFLoader for {filename} | extract_images={extract_images} | file_path={file_path}", flush=True)
            log.info(f"[DEBUG] Creating PyPDFLoader for {filename} | extract_images={extract_images}")
            loader_instance = PyPDFLoader(file_path, extract_images=extract_images)
            print(f"[DEBUG] PyPDFLoader created successfully for {filename}", flush=True)
            log.info(f"[DEBUG] PyPDFLoader created successfully for {filename}")
            return loader_instance
        
        # Check if Document Intelligence is configured
        use_doc_intel = (
            self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT") 
            and self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY")
        )
        
        # For non-PDF files, use original engine logic (Tika/DocIntel available for other file types)
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
        elif use_doc_intel and (
                file_ext in ["pdf", "xls", "xlsx", "docx", "ppt", "pptx"]
                or file_content_type
                in [
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ]
        ):
            loader = AzureAIDocumentIntelligenceLoader(
                file_path=file_path,
                api_endpoint=self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT"),
                api_key=self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY"),
            )
        else:
            if file_ext == "csv":
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
