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
        log.info(f"[Loader.load] Starting extraction: filename={filename}, content_type={file_content_type}, file_path={file_path}")
        log.info(f"[Loader.load] Engine: {self.engine}, kwargs: {list(self.kwargs.keys())}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            log.error(f"[Loader.load] File does not exist: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        log.info(f"[Loader.load] File exists, size: {file_size} bytes")
        
        try:
            loader = self._get_loader(filename, file_content_type, file_path)
            log.info(f"[Loader.load] Loader instance created: {type(loader).__name__}")
            
            docs = loader.load()
            log.info(f"[Loader.load] loader.load() returned {len(docs)} document(s)")
            
            if len(docs) > 0:
                total_chars = sum(len(doc.page_content) for doc in docs)
                log.info(f"[Loader.load] Total characters extracted: {total_chars}")
                log.info(f"[Loader.load] First doc preview: {docs[0].page_content[:200]}...")
            else:
                log.warning(f"[Loader.load] loader.load() returned 0 documents!")
        except Exception as e:
            log.error(f"[Loader.load] Error during extraction: {type(e).__name__}: {str(e)}", exc_info=True)
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
        log.info(f"[Loader._get_loader] filename={filename}, file_ext={file_ext}, content_type={file_content_type}, engine={self.engine}")

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
        else:
            if file_ext == "pdf":
                extract_images = self.kwargs.get("PDF_EXTRACT_IMAGES", False)
                log.info(f"[Loader._get_loader] Using PyPDFLoader for PDF: extract_images={extract_images}")
                log.info(f"[Loader._get_loader] PDF file_path: {file_path}")
                # Verify file exists and is readable
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    log.info(f"[Loader._get_loader] PDF file exists, size: {file_size} bytes")
                    # Try to read first few bytes to verify it's a PDF
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(4)
                            if header == b'%PDF':
                                log.info(f"[Loader._get_loader] ✅ File appears to be a valid PDF (starts with %PDF)")
                            else:
                                log.warning(f"[Loader._get_loader] ⚠️  File does not start with %PDF header: {header}")
                    except Exception as e:
                        log.warning(f"[Loader._get_loader] ⚠️  Could not read PDF header: {e}")
                else:
                    log.error(f"[Loader._get_loader] ❌ PDF file does not exist: {file_path}")
                loader = PyPDFLoader(
                    file_path, extract_images=extract_images
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
