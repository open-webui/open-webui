import logging
import re

from langchain_core.documents import Document

from open_webui.retrieval.loaders.main import DoclingLoader

log = logging.getLogger(__name__)


class DoclingLoaderJson(DoclingLoader):
    """Return the Docling JSON document payload split into vector-DB-friendly Documents.

    chunk_mode controls how the structured content is split:
      "item"  - one Document per Docling content item (finest granularity)
      "page"  - one Document per page
      "chunk" - sliding-window chunks with overlap (default)

    For "chunk" mode chunk_size and chunk_overlap are measured in the unit set by
    chunk_content_type: "character" (default) counts Unicode characters; "token" counts
    tiktoken subword tokens.  Both are absolute values, not fractions.
    The page number of every Document is taken from the first content item that
    falls into that chunk / page / item.
    """

    def __init__(
        self,
        *args,
        chunk_mode: str = "chunk",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        chunk_content_type: str = "character",
        tiktoken_encoding_name: str = "cl100k_base",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.chunk_mode = chunk_mode
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_content_type = chunk_content_type
        # Initialise tiktoken encoder if the unit is "token".
        self._enc = None
        if self.chunk_content_type == "token":
            try:
                import tiktoken
                self._enc = tiktoken.get_encoding(tiktoken_encoding_name)
            except Exception as exc:
                log.warning(
                    "tiktoken unavailable (%s); falling back to character-based chunking", exc
                )
                self.chunk_content_type = "character"
        to_formats = list(self.params.get("to_formats") or ["md"])
        if "json" not in to_formats:
            to_formats.append("json")
        self.params = {**self.params, "to_formats": to_formats}

    def _word_sizes(self, words: list[str]) -> list[int]:
        """Return the size of each word-token in the configured unit.

        "character" (default): number of Unicode characters.
        "token"               : tiktoken subword token count (approximate per word).
        """
        if self.chunk_content_type == "token" and self._enc is not None:
            return [len(self._enc.encode(w)) for w in words]
        return [len(w) for w in words]

    def _extract_ordered_items(self, document_data: dict) -> list[dict]:
        """Return all content items sorted by page then spatial position (top→bottom, left→right).

        Each entry: {"text": str, "label": str, "page_no": int, "bbox": tuple|None}
        Items without any prov entry containing a page_no are omitted.
        """
        json_content = document_data.get("json_content") or document_data.get("json") or {}

        items_out = []
        for name in ("texts", "tables", "pictures", "key_value_items"):
            cand = document_data.get(name) or (
                json_content.get(name) if isinstance(json_content, dict) else None
            )
            if not isinstance(cand, list):
                continue
            for it in cand:
                text = it.get("text") or it.get("orig") or ""
                label = it.get("label") or ""
                for prov_entry in it.get("prov") or []:
                    if not isinstance(prov_entry, dict):
                        continue
                    pno = prov_entry.get("page_no")
                    if not isinstance(pno, int):
                        continue
                    bbox = None
                    b = prov_entry.get("bbox")
                    if isinstance(b, dict):
                        try:
                            bbox = (
                                float(b.get("l", 0)),
                                float(b.get("t", 0)),
                                float(b.get("r", 0)),
                                float(b.get("b", 0)),
                            )
                        except Exception:
                            bbox = None
                    items_out.append(
                        {
                            "text": text,
                            "label": label,
                            "page_no": pno,
                            "bbox": bbox,
                            "level": it.get("level"),          # section_header depth
                            "marker": it.get("marker"),        # list_item bullet/number
                            "enumerated": it.get("enumerated"),# list_item ordered flag
                            "hyperlink": it.get("hyperlink"),  # hyperlink target if any
                        }
                    )
                    break  # first valid prov entry is sufficient for sorting/metadata

        def _sort_key(entry):
            b = entry["bbox"]
            if b:
                cy = (b[1] + b[3]) / 2.0
                cx = (b[0] + b[2]) / 2.0
                return (entry["page_no"], -cy, cx)  # -cy: PDF y-axis goes upward
            return (entry["page_no"], 0.0, 0.0)

        items_out.sort(key=_sort_key)
        return items_out

    def _extract_doc_metadata(self, document_data: dict) -> dict:
        """Extract document-level fields shared by every point produced from this document.

        These are stored per-point because the vector DB has no collection-level
        metadata store — all filterable/retrievable fields must live on each point.

        origin and name live inside json_content (the DoclingDocument), not at the
        outer ExportDocumentResponse level.
        """
        jc = document_data.get("json_content") or document_data.get("json") or {}
        if not isinstance(jc, dict):
            jc = {}
        origin = jc.get("origin") or {}
        meta: dict = {"Content-Type": "application/json"}
        if origin.get("filename"):
            meta["filename"] = origin["filename"]
        if origin.get("mimetype"):
            meta["source_mimetype"] = origin["mimetype"]
        if origin.get("uri"):
            meta["source_uri"] = origin["uri"]
        if origin.get("binary_hash") is not None:
            meta["binary_hash"] = str(origin["binary_hash"])
        name = jc.get("name") or document_data.get("name")
        if name:
            meta["document_name"] = name
        return meta

    def _format_item_mode(self, document_data: dict) -> list[Document]:
        """One Document per Docling content item."""
        items = self._extract_ordered_items(document_data)
        doc_meta = self._extract_doc_metadata(document_data)
        docs = []
        for it in items:
            text = it["text"]
            if not text:
                continue
            metadata = {
                **doc_meta,
                # The full Docling document (json_content/md_content) is intentionally NOT
                # attached here: item mode already exposes page/bbox/label/level/marker/etc.
                # as flat fields below, so the full per-item blob would just duplicate the
                # entire document's texts/tables/pictures/pages into every single chunk's
                # Qdrant payload for no benefit (nothing in this codebase reads it back).
                # Uncomment for local debugging only:
                # "docling_document": document_data,
                "page": it["page_no"],
                "label": it["label"],
                "chunk_mode": "item",
            }
            if it["bbox"]:
                metadata["bbox"] = it["bbox"]
            if it.get("level") is not None:
                metadata["level"] = it["level"]
            if it.get("marker"):
                metadata["marker"] = it["marker"]
            if it.get("enumerated") is not None:
                metadata["enumerated"] = it["enumerated"]
            if it.get("hyperlink"):
                metadata["hyperlink"] = it["hyperlink"]
            docs.append(Document(page_content=text, metadata=metadata))
        log.debug("Docling JSON item-mode produced %d documents", len(docs))
        return docs

    def _format_page_mode(self, document_data: dict) -> list[Document]:
        """One Document per page, all items on that page joined with newlines."""
        items = self._extract_ordered_items(document_data)
        doc_meta = self._extract_doc_metadata(document_data)
        jc = document_data.get("json_content") or document_data.get("json") or {}
        pages_map = (jc.get("pages") if isinstance(jc, dict) else None) or {}
        pages: dict[int, list[str]] = {}
        for it in items:
            text = it["text"]
            if not text:
                continue
            pages.setdefault(it["page_no"], []).append(text)
        docs = []
        for pno in sorted(pages.keys()):
            page_text = "\n".join(pages[pno])
            metadata = {
                **doc_meta,
                # Full document (json_content/md_content) intentionally omitted — see the
                # comment in _format_item_mode. Uncomment for local debugging only:
                # "docling_document": document_data,
                "page": pno,
                "chunk_mode": "page",
            }
            page_info = pages_map.get(str(pno)) or {}
            if isinstance(page_info, dict):
                # DoclingDocument serialises page size as {"size": {"width": …, "height": …}}
                size = page_info.get("size") or {}
                if size.get("width") is not None:
                    metadata["page_width"] = size["width"]
                if size.get("height") is not None:
                    metadata["page_height"] = size["height"]
            docs.append(Document(page_content=page_text, metadata=metadata))
        log.debug("Docling JSON page-mode produced %d documents", len(docs))
        return docs

    def _format_chunk_mode(self, document_data: dict) -> list[Document]:
        """Sliding-window chunks measured in the configured unit (characters or tiktoken tokens).

        Internally the text is tokenised word-by-word to preserve all whitespace and
        newlines. The window boundaries are determined by the cumulative size of those
        word-tokens in the requested unit so the assembled chunk text is lossless.

        chunk_size    – maximum chunk size in the configured unit.
        chunk_overlap – how many units of overlap to keep between consecutive chunks
                        (absolute, same unit as chunk_size).
        """
        items = self._extract_ordered_items(document_data)
        doc_meta = self._extract_doc_metadata(document_data)

        # Build a flat list of word-tokens and a parallel list of their page numbers.
        #
        # Docling hands back each structural item (heading, paragraph, list item, ...)
        # already stripped of leading/trailing whitespace -- it's structural output, not
        # flat markdown. Concatenating items back-to-back with nothing in between glues
        # e.g. a heading directly onto the next paragraph ("HeadingParagraph text...").
        # Insert an explicit paragraph-break token between items to keep the
        # reconstructed text readable.
        words: list[str] = []
        word_pages: list[int] = []
        for it in items:
            text = it["text"]
            if not text:
                continue
            if words:
                words.append('\n\n')
                word_pages.append(it["page_no"])
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            # Each whitespace run and each non-whitespace run becomes one token so
            # that joining with "".join() reconstructs the original text exactly.
            item_words = re.findall(r'\n|[ \t]+|[^\s]+', text)
            words.extend(item_words)
            word_pages.extend([it["page_no"]] * len(item_words))

        if not words:
            document_text = document_data.get("md_content") or document_data.get("text") or ""
            return [
                Document(
                    page_content=document_text,
                    # Full document intentionally omitted — see _format_item_mode.
                    # metadata={**doc_meta, "docling_document": document_data},
                    metadata=doc_meta,
                )
            ]

        # Per-word sizes in the configured unit.
        sizes = self._word_sizes(words)

        chunk_size = max(1, self.chunk_size)
        chunk_overlap = max(0, min(self.chunk_overlap, chunk_size - 1))
        step_size = max(1, chunk_size - chunk_overlap)

        n = len(words)
        docs = []
        start_idx = 0

        while start_idx < n:
            # Collect words until chunk_size units are accumulated.
            acc = 0
            end_idx = start_idx
            while end_idx < n:
                acc += sizes[end_idx]
                end_idx += 1
                if acc >= chunk_size:
                    break

            chunk_text = "".join(words[start_idx:end_idx])
            page_no = word_pages[start_idx]
            metadata = {
                **doc_meta,
                # Full document intentionally omitted — see the comment in
                # _format_item_mode. Uncomment for local debugging only:
                # "docling_document": document_data,
                "page": page_no,
                "chunk_mode": "chunk",
                "chunk_start_word": start_idx,
                "chunk_end_word": end_idx,
            }
            docs.append(Document(page_content=chunk_text, metadata=metadata))

            if end_idx >= n:
                break

            # Advance by step_size units from the current start.
            adv = 0
            new_start = start_idx
            while new_start < end_idx:
                adv += sizes[new_start]
                new_start += 1
                if adv >= step_size:
                    break
            # Guard: always advance by at least one word to prevent infinite loops.
            if new_start <= start_idx:
                new_start = start_idx + 1
            start_idx = new_start

        log.debug(
            "Docling JSON chunk-mode produced %d documents "
            "(chunk_size=%d %s, chunk_overlap=%d %s)",
            len(docs),
            chunk_size,
            self.chunk_content_type,
            chunk_overlap,
            self.chunk_content_type,
        )
        return docs

    def format_result(self, result_json: dict) -> list[Document]:
        document_data = result_json.get("document", {})
        json_content = document_data.get("json_content") or document_data.get("json")

        if isinstance(json_content, dict) and isinstance(json_content.get("pages"), dict):
            if self.chunk_mode == "item":
                return self._format_item_mode(document_data)
            elif self.chunk_mode == "page":
                return self._format_page_mode(document_data)
            else:  # "chunk" is the default
                return self._format_chunk_mode(document_data)

        # Fallback: structured JSON not available, return raw markdown/text.
        document_text = document_data.get("md_content") or document_data.get("text") or ""
        # Full document intentionally omitted here too — document_text above already IS
        # md_content, so attaching document_data again would duplicate it plus json_content
        # into metadata for no benefit. Uncomment for local debugging only:
        # metadata = {"Content-Type": "application/json", "docling_document": document_data}
        metadata = {"Content-Type": "application/json"}
        log.debug("Docling JSON result extracted (fallback): keys=%s", list(document_data.keys()))
        return [Document(page_content=document_text, metadata=metadata)]
