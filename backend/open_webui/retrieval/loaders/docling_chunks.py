"""
Docling chunking engine ("docling_chunks").

Lets docling-serve's HybridChunker cut the document along its own structure
(sections, paragraphs, tables, lists) instead of running Open WebUI's text
splitter over flat markdown.  Every chunk carries the heading path of its
section and its page, so retrieval finds a chunk by the section it belongs to
and citations open the right page.

Open WebUI's chunk settings are mapped onto the chunker:

* CHUNK_SIZE            -> chunking_max_tokens (minus the overlap, see below)
* CHUNK_OVERLAP         -> the tail of the previous chunk is prepended, but only
                           within the same section; HybridChunker has no overlap
                           of its own and cuts long sections mid-sentence
* CHUNK_MIN_SIZE_TARGET -> chunking_merge_peers (> 0 merges small neighbouring
                           chunks of the same section, which may span pages)

DOCLING_CHUNK_TOKENIZER (environment, Hugging Face model name) should match the
embedding model; docling-serve uses sentence-transformers/all-MiniLM-L6-v2 when
it is empty.

Chunks are final: process_file skips the text splitter for documents marked
with DOCLING_CHUNK_KEY and builds the stored file content from
DOCLING_SEGMENT_KEY, so overlap and repeated headings do not end up there.
"""

import logging
import os
import re
import time

import requests
from langchain_core.documents import Document

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL

log = logging.getLogger(__name__)

DOCLING_CHUNK_TOKENIZER = os.environ.get('DOCLING_CHUNK_TOKENIZER', '').strip()

# Metadata marking a chunk as final, and the chunk's share of the file content.
DOCLING_CHUNK_KEY = 'docling_chunk'
DOCLING_SEGMENT_KEY = 'docling_segment'

HEADING_SEPARATOR = ' > '
# Rough characters per token, used when CHUNK_SIZE is measured in characters.
CHARS_PER_TOKEN = 4
MIN_MAX_TOKENS = 32

SENTENCE_START = re.compile(r'(?<=[.!?:;])\s+(?=\S)|\n+(?=\S)')


class DoclingChunksLoader:
    # Seconds docling-serve may hold one status request open before answering.
    POLL_WAIT = 30

    def __init__(
        self,
        url,
        api_key=None,
        file_path=None,
        mime_type=None,
        params=None,
        timeout=None,
        chunk_size=1000,
        chunk_overlap=0,
        chunk_min_size_target=0,
        text_splitter='',
        tiktoken_encoding_name='cl100k_base',
    ):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.file_path = file_path
        self.mime_type = mime_type
        self.params = params or {}
        self.timeout = timeout
        self.text_splitter = text_splitter or 'character'
        self.tiktoken_encoding_name = tiktoken_encoding_name or 'cl100k_base'
        self.chunk_size = _positive_int(chunk_size, 1000)
        self.chunk_overlap = min(_positive_int(chunk_overlap, 0), self.chunk_size // 2)
        self.merge_peers = _positive_int(chunk_min_size_target, 0) > 0
        self._encoding = None

    # Size measurement ---------------------------------------------------

    def _uses_tokens(self) -> bool:
        return self.text_splitter in ('token', 'token_transformers')

    def _max_tokens(self) -> int:
        size = self.chunk_size - self.chunk_overlap
        if not self._uses_tokens():
            size //= CHARS_PER_TOKEN
        return max(MIN_MAX_TOKENS, size)

    def _tokenize(self, text: str) -> list | None:
        if not self._uses_tokens():
            return None
        try:
            if self._encoding is None:
                import tiktoken

                self._encoding = tiktoken.get_encoding(self.tiktoken_encoding_name)
            return self._encoding.encode(text, disallowed_special=())
        except Exception as e:
            log.warning('Docling chunks: tiktoken unavailable (%s), measuring overlap in characters', e)
            self.text_splitter = 'character'
            return None

    def _tail(self, text: str) -> str:
        """The last CHUNK_OVERLAP units of `text`, starting at a sentence or word boundary."""
        if not self.chunk_overlap or not text:
            return ''
        tokens = self._tokenize(text)
        if tokens is not None:
            if len(tokens) <= self.chunk_overlap:
                return text
            tail = self._encoding.decode(tokens[-self.chunk_overlap :])
        else:
            if len(text) <= self.chunk_overlap:
                return text
            tail = text[-self.chunk_overlap :]

        # Prefer a sentence start, as long as it keeps at least half of the overlap.
        match = SENTENCE_START.search(tail)
        if match and match.end() <= len(tail) // 2:
            return tail[match.end() :]
        # Otherwise drop the cut-off word at the front.
        space = re.search(r'\s+', tail)
        if space and space.end() < len(tail):
            return tail[space.end() :]
        return tail

    # docling-serve ------------------------------------------------------

    def load(self) -> list[Document]:
        task_id = self._submit()
        self._wait(task_id)
        r = requests.get(
            f'{self.url}/v1/result/{task_id}',
            headers=self._headers(),
            verify=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=120,
        )
        self._raise_for_response(r, 'result')
        return self._parse(r.json())

    def _headers(self) -> dict:
        return {'X-Api-Key': f'{self.api_key}'} if self.api_key else {}

    def _raise_for_response(self, r: requests.Response, action: str) -> None:
        if r.ok:
            return
        error_msg = f'Error calling Docling API: {r.reason}'
        if r.text:
            try:
                error_data = r.json()
                if 'detail' in error_data:
                    error_msg += f' - {error_data["detail"]}'
            except Exception:
                error_msg += f' - {r.text}'
        raise Exception(f'Error calling Docling ({action}): {error_msg}')

    def _wait(self, task_id: str) -> None:
        deadline = time.monotonic() + self.timeout if self.timeout else None
        while True:
            wait = self.POLL_WAIT
            if deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise Exception(f'Error calling Docling: chunking timed out after {self.timeout} seconds')
                wait = max(1, min(wait, int(remaining)))

            try:
                r = requests.get(
                    f'{self.url}/v1/status/poll/{task_id}',
                    params={'wait': wait},
                    headers=self._headers(),
                    verify=AIOHTTP_CLIENT_SESSION_SSL,
                    timeout=wait + 30,
                )
            except requests.Timeout:
                log.warning('Docling status request for task %s timed out, retrying', task_id)
                continue
            self._raise_for_response(r, 'status')

            task = r.json()
            task_status = task.get('task_status')
            if task_status == 'success':
                return
            if task_status == 'failure':
                raise Exception(f'Error calling Docling: chunking failed (task {task_id})')
            log.debug('Docling task %s: %s, queue position %s', task_id, task_status, task.get('task_position'))

    def _submit(self) -> str:
        data = {
            'convert_image_export_mode': 'placeholder',
            # Conversion options (OCR, picture description, ...) as configured for Docling;
            # the chunk endpoints expect them prefixed with "convert_".
            **{
                key if key.startswith(('convert_', 'chunking_')) else f'convert_{key}': value
                for key, value in self.params.items()
            },
            'chunking_include_raw_text': 'true',
            'chunking_use_markdown_tables': 'true',
            'chunking_max_tokens': str(self._max_tokens()),
            'chunking_merge_peers': 'true' if self.merge_peers else 'false',
        }
        if DOCLING_CHUNK_TOKENIZER:
            data['chunking_tokenizer'] = DOCLING_CHUNK_TOKENIZER

        with open(self.file_path, 'rb') as f:
            r = requests.post(
                f'{self.url}/v1/chunk/hybrid/file/async',
                files={
                    'files': (
                        os.path.basename(self.file_path),
                        f,
                        self.mime_type or 'application/octet-stream',
                    )
                },
                data=data,
                headers=self._headers(),
                verify=AIOHTTP_CLIENT_SESSION_SSL,
            )
        self._raise_for_response(r, 'submit')
        task_id = r.json().get('task_id')
        if not task_id:
            raise Exception('Error calling Docling: no task id returned')
        log.info(
            'Docling chunking task %s submitted for %s (max_tokens=%s, merge_peers=%s, overlap=%s)',
            task_id,
            os.path.basename(self.file_path),
            data['chunking_max_tokens'],
            data['chunking_merge_peers'],
            self.chunk_overlap,
        )
        return task_id

    def _parse(self, result: dict) -> list[Document]:
        for error in result.get('errors') or []:
            if isinstance(error, dict) and error.get('error_message'):
                log.warning('Docling chunking reported: %s', error['error_message'])

        chunks = [c for c in result.get('chunks') or [] if isinstance(c, dict)]
        chunks.sort(key=lambda c: c.get('chunk_index') if isinstance(c.get('chunk_index'), int) else 0)

        metadata = {'Content-Type': self.mime_type} if self.mime_type else {}
        documents = []
        previous_raw = ''
        previous_path = None
        previous_pages = []
        for chunk in chunks:
            headings = [h.strip() for h in chunk.get('headings') or [] if isinstance(h, str) and h.strip()]
            path = HEADING_SEPARATOR.join(headings)
            raw = _raw_text(chunk, headings).strip()
            if not raw:
                continue
            pages = sorted({p for p in chunk.get('page_numbers') or [] if isinstance(p, int) and p > 0})

            # Overlap carries a thought across a cut inside one section. Without headings the
            # whole file is one "section", so the previous chunk must also be on this or the
            # preceding page, otherwise the overlap would pull in text from elsewhere.
            continues = path == previous_path and (
                not pages or not previous_pages or 0 <= pages[0] - previous_pages[-1] <= 1
            )
            overlap = self._tail(previous_raw) if continues else ''
            # Docling cuts long sections mid-sentence; keep such a sentence on one line.
            joiner = '\n\n' if re.search(r'[.!?:;]\s*$|\n\s*$', previous_raw) else ' '
            body = f'{overlap}{joiner}{raw}' if overlap else raw
            content = f'{path}\n\n{body}' if path else body
            # Stored file content: each heading path once, no overlap.
            segment = f'{path}\n\n{raw}' if path and path != previous_path else raw

            chunk_metadata = {**metadata, DOCLING_CHUNK_KEY: True, DOCLING_SEGMENT_KEY: segment}
            if path:
                chunk_metadata['headings'] = path
            if pages:
                # Citations use 0-based pages; Docling counts from 1.
                chunk_metadata['page'] = pages[0] - 1
                if len(pages) > 1:
                    chunk_metadata['page_end'] = pages[-1] - 1

            documents.append(Document(page_content=content, metadata=chunk_metadata))
            previous_raw, previous_path, previous_pages = raw, path, pages

        if not documents:
            raise Exception('Error calling Docling: the document produced no chunks')
        log.debug('Docling chunking produced %d chunks', len(documents))
        return documents


def _positive_int(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value >= 0 else default


def _raw_text(chunk: dict, headings: list[str]) -> str:
    """Chunk text without the heading lines docling-serve puts in front of it."""
    raw = chunk.get('raw_text')
    if isinstance(raw, str):
        return raw
    text = chunk.get('text') if isinstance(chunk.get('text'), str) else ''
    prefix = '\n'.join(headings)
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text
