import logging
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree.ElementTree import ParseError

from langchain_core.documents import Document

log = logging.getLogger(__name__)

ALLOWED_SCHEMES = {'http', 'https'}
ALLOWED_NETLOCS = {
    'youtu.be',
    'm.youtube.com',
    'youtube.com',
    'www.youtube.com',
    'www.youtube-nocookie.com',
    'vid.plus',
}


def _parse_video_id(url: str) -> str | None:
    """Parse a YouTube URL and return the video ID if valid, otherwise None."""
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ALLOWED_SCHEMES:
        return None

    if parsed_url.netloc not in ALLOWED_NETLOCS:
        return None

    path = parsed_url.path

    if path.endswith('/watch'):
        query = parsed_url.query
        parsed_query = parse_qs(query)
        if 'v' in parsed_query:
            ids = parsed_query['v']
            video_id = ids if isinstance(ids, str) else ids[0]
        else:
            return None
    else:
        path = parsed_url.path.lstrip('/')
        video_id = path.split('/')[-1]

    if len(video_id) != 11:  # Video IDs are 11 characters long
        return None

    return video_id


class YoutubeLoader:
    """Load `YouTube` video transcripts."""

    def __init__(
        self,
        video_id: str,
        language: str | Sequence[str] = 'en',
        proxy_url: str | None = None,
    ):
        """Initialize with YouTube video ID."""
        _video_id = _parse_video_id(video_id)
        self.video_id = _video_id if _video_id is not None else video_id
        self._metadata = {'source': video_id}
        self.proxy_url = proxy_url

        # Ensure language is a list
        if isinstance(language, str):
            self.language = [language]
        else:
            self.language = list(language)

        # Add English as fallback if not already in the list
        if 'en' not in self.language:
            self.language.append('en')

    def _get_transcript_api(self):
        try:
            from youtube_transcript_api import NoTranscriptFound, YouTubeTranscriptApi
            from youtube_transcript_api.proxies import GenericProxyConfig
        except ImportError:
            raise ImportError(
                'Could not import "youtube_transcript_api" Python package. '
                'Please install it with `pip install youtube-transcript-api`.'
            )

        youtube_proxies = None
        if self.proxy_url:
            youtube_proxies = GenericProxyConfig(http_url=self.proxy_url, https_url=self.proxy_url)
            log.debug(f'Using proxy URL: {self.proxy_url[:14]}...')

        return NoTranscriptFound, YouTubeTranscriptApi(proxy_config=youtube_proxies)

    def _fetch_transcript_text(self, transcript) -> tuple[str | None, str | None]:
        try:
            transcript_pieces: Sequence[Any] = transcript.fetch()
        except ParseError:
            return None, 'invalid'

        if not transcript_pieces:
            return None, 'empty'

        return (
            ' '.join(
                map(
                    lambda transcript_piece: getattr(transcript_piece, 'text', '').strip(' '),
                    transcript_pieces,
                )
            ),
            None,
        )

    def _load_transcript_for_language(self, transcript_list, lang: str, no_transcript_found):
        transcript = transcript_list.find_transcript([lang])
        if transcript.is_generated:
            log.debug(f"Found generated transcript for language '{lang}'")
            try:
                transcript = transcript_list.find_manually_created_transcript([lang])
                log.debug(f"Found manual transcript for language '{lang}'")
            except no_transcript_found:
                log.debug(f"No manual transcript found for language '{lang}', using generated")

        log.debug(f"Found transcript for language '{lang}'")
        transcript_text, transcript_error = self._fetch_transcript_text(transcript)
        if transcript_text is None:
            if transcript_error == 'invalid':
                log.debug(f"Empty or invalid transcript for language '{lang}'")
            else:
                log.debug(f"Empty transcript for language '{lang}'")
            return None

        return [Document(page_content=transcript_text, metadata=self._metadata)]

    def load(self) -> list[Document]:
        """Load YouTube transcripts into `Document` objects."""
        NoTranscriptFound, transcript_api = self._get_transcript_api()
        try:
            transcript_list = transcript_api.list(self.video_id)
        except Exception:
            log.exception('Loading YouTube transcript failed')
            return []

        # Try each language in order of priority
        for lang in self.language:
            try:
                documents = self._load_transcript_for_language(transcript_list, lang, NoTranscriptFound)
                if documents is not None:
                    return documents
            except NoTranscriptFound:
                log.debug(f"No transcript found for language '{lang}'")
                continue
            except Exception as e:
                log.info(f"Error finding transcript for language '{lang}'")
                raise e

        # If we get here, all languages failed
        languages_tried = ', '.join(self.language)
        log.warning(
            'No transcript found for any of the specified languages: '
            f'{languages_tried}. Verify if the video has transcripts, '
            'add more languages if needed.'
        )
        raise NoTranscriptFound(self.video_id, self.language, list(transcript_list))

    async def aload(self) -> list[Document]:
        """Asynchronously load YouTube transcripts into `Document` objects."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load)
