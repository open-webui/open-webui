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

    def _get_video_title(self) -> Optional[str]:
        """Get the video title using YouTube API or page scraping."""
        try:
            import requests
            import json

            # First try using YouTube Data API v3 if available
            try:
                from open_webui.config import YOUTUBE_API_KEY

                if YOUTUBE_API_KEY:
                    url = f"https://www.googleapis.com/youtube/v3/videos?id={self.video_id}&key={YOUTUBE_API_KEY}&part=snippet"
                    response = requests.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("items"):
                            return data["items"][0]["snippet"]["title"]
            except ImportError:
                pass

            # Fallback to scraping the title from YouTube page
            url = f"https://www.youtube.com/watch?v={self.video_id}"
            response = requests.get(url)
            if response.status_code == 200:
                import re

                title_match = re.search(r"<title>(.+?)</title>", response.text)
                if title_match:
                    title = title_match.group(1)
                    return title
            return None
        except Exception as e:
            print(f"Error getting video title: {e}")
            return None

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
            # First try to get manual transcript in requested language
            for lang in self.language:
                try:
                    available_transcripts = (
                        transcript_list._manually_created_transcripts
                    )
                    if lang in available_transcripts:
                        transcript = available_transcripts[lang]
                        log.info(f"Found manual transcript in language: {lang}")
                        break
                except NoTranscriptFound:
                    continue
            else:
                # If no manual transcript found, try auto-generated ones
                try:
                    transcript = transcript_list.find_transcript(self.language)
                    log.info(
                        f"Using auto-generated transcript in language: {transcript.language_code}"
                    )
                except NoTranscriptFound:
                    # Final fallback: try to get any available transcript
                    available_transcripts = list(
                        transcript_list._manually_created_transcripts.values()
                    ) + list(transcript_list._generated_transcripts.values())
                    if available_transcripts:
                        transcript = available_transcripts[0]
                        log.info(
                            f"Using first available transcript in language: {transcript.language_code}"
                        )
                    else:
                        log.error("No transcripts found for video")
                        return []

        except Exception as e:
            log.exception(f"Error fetching transcript: {str(e)}")
            return []

        transcript_pieces: List[Dict[str, Any]] = transcript.fetch()

        # Get video title and add it to base metadata
        title = self._get_video_title()
        if title:
            self._metadata["title"] = title

        # Add the base video URL to metadata
        base_url = f"https://www.youtube.com/watch?v={self.video_id}"
        self._metadata["source_url"] = base_url

        # Combine pieces into a single text while tracking timestamp positions
        full_text = ""
        timestamp_map = []

        for piece in transcript_pieces:
            start_char = len(full_text)
            text = piece["text"].strip()
            full_text += text + " "
            end_char = len(full_text)

            timestamp_map.append(
                {
                    "start": start_char,
                    "end": end_char,
                    "time": piece["start"],
                    "duration": piece["duration"],
                }
            )

        # Create a single document that will be split by Langchain's text splitter
        doc = Document(
            page_content=full_text.strip(),
            metadata={
                **self._metadata,
                "timestamp_map": timestamp_map,  # Store timestamp mapping in metadata
            },
        )

        return [doc]
