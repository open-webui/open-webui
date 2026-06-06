import logging

from open_webui.models.files import Files

log = logging.getLogger(__name__)

DOCUMENT_CONTEXT_MAX_CHARS = 2000


def normalize_document_context_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def build_document_context(text: str, limit: int = DOCUMENT_CONTEXT_MAX_CHARS) -> str:
    normalized_text = normalize_document_context_text(text)
    if not normalized_text:
        return ""

    if len(normalized_text) <= limit:
        return normalized_text

    return normalized_text[:limit].rstrip()


def get_file_document_context(file_id: str) -> str:
    if not file_id:
        return ""

    try:
        file = Files.get_file_by_id(file_id)
        if not file or not file.data:
            return ""

        return build_document_context(file.data.get("content", ""))
    except Exception as e:
        log.debug(f"Failed to build document context for file {file_id}: {e}")
        return ""


def format_document_with_context(document: str, context: str) -> str:
    if not context:
        return document

    normalized_document = normalize_document_context_text(document)
    normalized_context = normalize_document_context_text(context)

    if normalized_document and normalized_document.startswith(normalized_context):
        return document

    if not document:
        return f"Document Context:\n{context}"

    return f"Document Context:\n{context}\n\nRelevant Chunk:\n{document}"


def enrich_documents_with_context(
    documents: list[str], metadatas: list[dict]
) -> tuple[list[str], list[dict]]:
    if not documents or not metadatas:
        return documents, metadatas

    enriched_documents = []
    enriched_metadatas = []
    context_cache: dict[str, str] = {}

    for document, metadata in zip(documents, metadatas):
        metadata = metadata or {}
        file_id = metadata.get("file_id", "")

        if file_id not in context_cache:
            context_cache[file_id] = get_file_document_context(file_id)

        context = context_cache[file_id]
        enriched_documents.append(format_document_with_context(document, context))
        enriched_metadatas.append(
            {
                **metadata,
                **({"document_context": context} if context else {}),
            }
        )

    return enriched_documents, enriched_metadatas