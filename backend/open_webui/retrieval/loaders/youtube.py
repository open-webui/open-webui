import logging
from typing import Any, Dict, Generator, List, Optional, Sequence, Union
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


class YoutubeTranscriptError(Exception):
    """A YouTube transcript could not be retrieved."""


def _transcript_error_message(error: Exception, video_id: str) -> str:
    name = type(error).__name__

    if name in {'RequestBlocked', 'IpBlocked'}:
        return (
            f'YouTube blocked the transcript request for {video_id} from this server. '
            'This usually means the server address is rate limited or belongs to a cloud '
            'provider. A proxy for these requests can be configured under Admin Settings, '
            'Web Search, Youtube Proxy URL.'
        )
    if name == 'TranscriptsDisabled':
        return f'Transcripts are disabled for the YouTube video {video_id}.'
    if name == 'AgeRestricted':
        return f'The YouTube video {video_id} is age restricted, so its transcript cannot be retrieved.'
    if name in {'VideoUnavailable', 'VideoUnplayable', 'InvalidVideoId'}:
        return f'The YouTube video {video_id} is unavailable.'
    if name == 'PoTokenRequired':
        return f'YouTube requires additional verification to return the transcript for {video_id}.'

    return f'Could not retrieve a transcript for the YouTube video {video_id}.'


def _parse_video_id(url: str) -> Optional[str]:
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
        language: Union[str, Sequence[str]] = 'en',
        proxy_url: Optional[str] = None,
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

    def load(self) -> List[Document]:
        """Load YouTube transcripts into `Document` objects."""
        try:
            from youtube_transcript_api import (
                NoTranscriptFound,
                TranscriptsDisabled,
                YouTubeTranscriptApi,
            )
            from youtube_transcript_api.proxies import GenericProxyConfig
        except ImportError:
            raise ImportError(
                'Could not import "youtube_transcript_api" Python package. '
                'Please install it with `pip install youtube-transcript-api`.'
            )

        if self.proxy_url:
            youtube_proxies = GenericProxyConfig(http_url=self.proxy_url, https_url=self.proxy_url)
            log.debug('Using proxy URL: %s...', self.proxy_url[:14])
        else:
            youtube_proxies = None

        transcript_api = YouTubeTranscriptApi(proxy_config=youtube_proxies)
        try:
            transcript_list = transcript_api.list(self.video_id)
        except Exception as e:
            log.warning('Loading YouTube transcript failed: %s', e)
            raise YoutubeTranscriptError(_transcript_error_message(e, self.video_id)) from e

        # Try each language in order of priority
        for lang in self.language:
            try:
                transcript = transcript_list.find_transcript([lang])
                if transcript.is_generated:
                    log.debug("Found generated transcript for language '%s'", lang)
                    try:
                        transcript = transcript_list.find_manually_created_transcript([lang])
                        log.debug("Found manual transcript for language '%s'", lang)
                    except NoTranscriptFound:
                        log.debug("No manual transcript found for language '%s', using generated", lang)
                        pass

                log.debug("Found transcript for language '%s'", lang)
                try:
                    transcript_pieces: List[Dict[str, Any]] = transcript.fetch()
                except ParseError:
                    log.debug("Empty or invalid transcript for language '%s'", lang)
                    continue

                if not transcript_pieces:
                    log.debug("Empty transcript for language '%s'", lang)
                    continue

                transcript_text = ' '.join(
                    map(
                        lambda transcript_piece: (
                            transcript_piece.text.strip(' ') if hasattr(transcript_piece, 'text') else ''
                        ),
                        transcript_pieces,
                    )
                )
                return [Document(page_content=transcript_text, metadata=self._metadata)]
            except NoTranscriptFound:
                log.debug("No transcript found for language '%s'", lang)
                continue
            except Exception as e:
                log.info("Error finding transcript for language '%s'", lang)
                raise YoutubeTranscriptError(_transcript_error_message(e, self.video_id)) from e

        # If we get here, all languages failed
        languages_tried = ', '.join(self.language)
        log.warning(
            f'No transcript found for any of the specified languages: {languages_tried}. Verify if the video has transcripts, add more languages if needed.'
        )
        raise YoutubeTranscriptError(
            f'No transcript found for the YouTube video {self.video_id} in these languages: {languages_tried}.'
        )

    async def aload(self) -> Generator[Document, None, None]:
        """Asynchronously load YouTube transcripts into `Document` objects."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load)
