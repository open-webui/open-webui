import logging

from typing import Any, Dict, Generator, List, Optional, Sequence, Union
from urllib.parse import parse_qs, urlparse
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_NETLOCS = {
    "youtu.be",
    "m.youtube.com",
    "youtube.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
    "vid.plus",
}


def _parse_video_id(url: str) -> Optional[str]:
    """Parse a YouTube URL and return the video ID if valid, otherwise None."""
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ALLOWED_SCHEMES:
        return None

    if parsed_url.netloc not in ALLOWED_NETLOCS:
        return None

    path = parsed_url.path

    if path.endswith("/watch"):
        query = parsed_url.query
        parsed_query = parse_qs(query)
        if "v" in parsed_query:
            ids = parsed_query["v"]
            video_id = ids if isinstance(ids, str) else ids[0]
        else:
            return None
    else:
        path = parsed_url.path.lstrip("/")
        video_id = path.split("/")[-1]

    if len(video_id) != 11:  # Video IDs are 11 characters long
        return None

    return video_id


class YoutubeLoader:
    """Load `YouTube` video transcripts."""

    def __init__(
        self,
        video_id: str,
        language: Union[str, Sequence[str]] = "en",
        proxy_url: Optional[str] = None,
    ):
        """Initialize with YouTube video ID."""
        _video_id = _parse_video_id(video_id)
        self.video_id = _video_id if _video_id is not None else video_id
        self._metadata = {"source": video_id}
        self.language = language
        self.proxy_url = proxy_url
        if isinstance(language, str):
            self.language = [language]
        else:
            self.language = language

    def load(self) -> List[Document]:
        """Load YouTube transcripts into `Document` objects."""
        try:
            from youtube_transcript_api import (
                NoTranscriptFound,
                TranscriptsDisabled,
                YouTubeTranscriptApi,
            )
        except ImportError:
            raise ImportError(
                'Could not import "youtube_transcript_api" Python package. '
                "Please install it with `pip install youtube-transcript-api`."
            )

        if self.proxy_url:
            youtube_proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }
            # Don't log complete URL because it might contain secrets
            log.debug(f"Using proxy URL: {self.proxy_url[:14]}...")
        else:
            youtube_proxies = None

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(
                self.video_id, proxies=youtube_proxies
            )
        except Exception as e:
            log.exception("Loading YouTube transcript failed")
            return []

        try:
            transcript = transcript_list.find_transcript(self.language)
        except NoTranscriptFound:
            transcript = transcript_list.find_transcript(["en"])

        transcript_pieces: List[Dict[str, Any]] = transcript.fetch()

        transcript = " ".join(
            map(
                lambda transcript_piece: transcript_piece.text.strip(" "),
                transcript_pieces,
            )
        )
        return [Document(page_content=transcript, metadata=self._metadata)]
