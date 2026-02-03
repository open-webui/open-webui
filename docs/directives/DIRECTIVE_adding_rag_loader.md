# Directive: Adding a RAG Document Loader

> **Pattern type:** Backend feature extension
> **Complexity:** Medium
> **Files touched:** 2-3

---

## Prerequisites

- `ADR_006_rag_architecture.md` — RAG pipeline design
- `DOMAIN_GLOSSARY.md` — RAG, Embedding terms

---

## Structural Pattern

When adding support for a new document type in RAG:

1. **Create loader class** that parses the document format
2. **Return LangChain Documents** with content and metadata
3. **Register in loader factory** for automatic selection
4. **Handle dependencies gracefully** with import checks

| Component | Location | Purpose |
|-----------|----------|---------|
| Loader class | `backend/open_webui/retrieval/loaders/{type}.py` | Document parsing |
| Factory registration | `backend/open_webui/retrieval/loaders/main.py` | Loader selection |
| Dependencies | `pyproject.toml` | Optional packages |

---

## Illustrative Application

The YouTube loader (`backend/open_webui/retrieval/loaders/youtube.py`) demonstrates this pattern:

### Step 1: Create Loader Class

```python
# backend/open_webui/retrieval/loaders/youtube.py
import logging
from typing import List, Union, Sequence
from langchain_core.documents import Document

log = logging.getLogger(__name__)


class YoutubeLoader:
    """Load YouTube video transcripts as documents."""

    def __init__(
        self,
        video_id: str,
        language: Union[str, Sequence[str]] = "en",
    ):
        """
        Initialize with YouTube video ID.

        Args:
            video_id: The YouTube video ID (e.g., 'dQw4w9WgXcQ')
            language: Language code(s) for transcript
        """
        self.video_id = video_id
        self._metadata = {"source": f"youtube:{video_id}"}
        self.language = [language] if isinstance(language, str) else list(language)

    def load(self) -> List[Document]:
        """
        Load YouTube transcript into Document objects.

        Returns:
            List of Documents containing transcript text
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise ImportError(
                'Could not import "youtube_transcript_api" Python package. '
                "Please install it with `pip install youtube-transcript-api`."
            )

        try:
            # Fetch transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(self.video_id)

            # Try to get transcript in preferred language
            transcript = None
            for lang in self.language:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            if transcript is None:
                # Fall back to auto-generated
                transcript = transcript_list.find_generated_transcript(self.language)

            # Extract text
            transcript_data = transcript.fetch()
            full_text = " ".join([entry["text"] for entry in transcript_data])

            return [
                Document(
                    page_content=full_text,
                    metadata={
                        **self._metadata,
                        "language": transcript.language_code,
                    },
                )
            ]

        except Exception as e:
            log.error(f"Error loading YouTube transcript: {e}")
            raise

    async def aload(self) -> List[Document]:
        """Async wrapper for load()."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load)
```

### Step 2: Register in Loader Factory

```python
# backend/open_webui/retrieval/loaders/main.py
from typing import List, Optional
from langchain_core.documents import Document
import mimetypes
import os

from open_webui.retrieval.loaders.youtube import YoutubeLoader
# Import other loaders...


def get_loader_for_file(
    file_path: str,
    file_type: Optional[str] = None,
) -> Optional[object]:
    """
    Get appropriate loader for file type.

    Args:
        file_path: Path to file or URL
        file_type: Explicit file type override

    Returns:
        Loader instance or None if unsupported
    """
    # Detect type if not provided
    if file_type is None:
        if file_path.startswith("https://youtube.com") or \
           file_path.startswith("https://www.youtube.com") or \
           file_path.startswith("https://youtu.be"):
            file_type = "youtube"
        else:
            file_type = mimetypes.guess_type(file_path)[0]

    # Map types to loaders
    loaders = {
        "youtube": lambda: YoutubeLoader(extract_video_id(file_path)),
        "application/pdf": lambda: PDFLoader(file_path),
        "text/plain": lambda: TextLoader(file_path),
        "text/markdown": lambda: MarkdownLoader(file_path),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            lambda: DocxLoader(file_path),
        # Add more type mappings...
    }

    loader_factory = loaders.get(file_type)
    if loader_factory:
        return loader_factory()

    return None


def load_document(
    file_path: str,
    file_type: Optional[str] = None,
) -> List[Document]:
    """
    Load document using appropriate loader.

    Args:
        file_path: Path to file or URL
        file_type: Explicit file type override

    Returns:
        List of Documents

    Raises:
        ValueError: If file type is not supported
    """
    loader = get_loader_for_file(file_path, file_type)

    if loader is None:
        raise ValueError(f"Unsupported file type: {file_type or file_path}")

    return loader.load()


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    import re

    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
        r'youtube\.com/embed/([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from: {url}")
```

### Step 3: Add Optional Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
youtube = [
    "youtube-transcript-api>=0.6.0",
]

# Or add to main dependencies if always needed
```

---

## Transfer Prompt

**When you need to add support for a new document type:**

1. **Create loader class:** `backend/open_webui/retrieval/loaders/{type}.py`

   ```python
   from typing import List
   from langchain_core.documents import Document

   class MyFormatLoader:
       def __init__(self, file_path: str, **options):
           self.file_path = file_path
           self.options = options

       def load(self) -> List[Document]:
           # Check for optional dependencies
           try:
               import required_package
           except ImportError:
               raise ImportError("Install with: pip install required-package")

           # Parse file
           content = parse_my_format(self.file_path)

           # Return as Documents
           return [
               Document(
                   page_content=content,
                   metadata={
                       "source": self.file_path,
                       "type": "my_format",
                   }
               )
           ]

       async def aload(self) -> List[Document]:
           import asyncio
           return await asyncio.get_event_loop().run_in_executor(
               None, self.load
           )
   ```

2. **Register in factory:** `backend/open_webui/retrieval/loaders/main.py`

   ```python
   from open_webui.retrieval.loaders.my_format import MyFormatLoader

   loaders = {
       # ...existing loaders...
       "application/x-my-format": lambda: MyFormatLoader(file_path),
   }
   ```

3. **Add dependencies** to `pyproject.toml` if needed

4. **Handle errors gracefully:**
   - Check for optional imports
   - Provide helpful error messages
   - Log parsing failures

**Loader requirements:**
- Must return `List[Document]` from LangChain
- Include metadata with at least `source`
- Implement both `load()` and `aload()` methods
- Handle import errors for optional dependencies

**Signals that this pattern applies:**
- Users request support for new file type
- Need to ingest data from new source
- Integrating with external content service

---

## Related Documents

- `ADR_006_rag_architecture.md` — RAG design decisions
- `backend/open_webui/retrieval/loaders/youtube.py` — Reference
- `DOMAIN_GLOSSARY.md` — RAG terminology

---

*Last updated: 2026-02-03*
