from open_webui.utils.multimodal import (
    build_media_content_parts,
    get_media_content_part_type,
    get_media_content_part_url,
    is_inline_media_data_url,
)


class TestGetMediaContentPartType:
    def test_image_by_type(self):
        assert get_media_content_part_type({'type': 'image'}) == 'image_url'

    def test_image_by_content_type(self):
        assert get_media_content_part_type({'type': 'file', 'content_type': 'image/png'}) == 'image_url'

    def test_video_by_type(self):
        assert get_media_content_part_type({'type': 'video'}) == 'video_url'

    def test_video_by_content_type(self):
        # Videos are uploaded as generic files, so the content type is what identifies them.
        assert get_media_content_part_type({'type': 'file', 'content_type': 'video/mp4'}) == 'video_url'

    def test_non_media_file(self):
        assert get_media_content_part_type({'type': 'file', 'content_type': 'application/pdf'}) is None

    def test_missing_content_type(self):
        assert get_media_content_part_type({'type': 'file'}) is None

    def test_non_dict(self):
        assert get_media_content_part_type(None) is None
        assert get_media_content_part_type('video/mp4') is None


class TestBuildMediaContentParts:
    def test_video_file_becomes_video_url_part(self):
        files = [{'type': 'file', 'content_type': 'video/mp4', 'url': 'file-id-1'}]
        assert build_media_content_parts(files) == [{'type': 'video_url', 'video_url': {'url': 'file-id-1'}}]

    def test_image_file_becomes_image_url_part(self):
        files = [{'type': 'image', 'url': 'file-id-1'}]
        assert build_media_content_parts(files) == [{'type': 'image_url', 'image_url': {'url': 'file-id-1'}}]

    def test_non_media_files_are_ignored(self):
        files = [
            {'type': 'file', 'content_type': 'application/pdf', 'url': 'file-id-1'},
            {'type': 'collection', 'url': 'file-id-2'},
        ]
        assert build_media_content_parts(files) == []

    def test_files_without_url_are_skipped(self):
        files = [
            {'type': 'file', 'content_type': 'video/mp4'},
            {'type': 'file', 'content_type': 'video/mp4', 'url': ''},
        ]
        assert build_media_content_parts(files) == []

    def test_parts_are_grouped_by_media_kind(self):
        files = [
            {'type': 'file', 'content_type': 'video/mp4', 'url': 'video-1'},
            {'type': 'image', 'url': 'image-1'},
            {'type': 'file', 'content_type': 'video/webm', 'url': 'video-2'},
        ]
        assert build_media_content_parts(files) == [
            {'type': 'image_url', 'image_url': {'url': 'image-1'}},
            {'type': 'video_url', 'video_url': {'url': 'video-1'}},
            {'type': 'video_url', 'video_url': {'url': 'video-2'}},
        ]

    def test_empty_input(self):
        assert build_media_content_parts([]) == []
        assert build_media_content_parts(None) == []


class TestGetMediaContentPartUrl:
    def test_video_part(self):
        item = {'type': 'video_url', 'video_url': {'url': 'file-id-1'}}
        assert get_media_content_part_url(item) == ('video_url', 'file-id-1')

    def test_image_part(self):
        item = {'type': 'image_url', 'image_url': {'url': 'file-id-1'}}
        assert get_media_content_part_url(item) == ('image_url', 'file-id-1')

    def test_text_part_is_not_media(self):
        assert get_media_content_part_url({'type': 'text', 'text': 'hello'}) is None

    def test_malformed_media_part(self):
        assert get_media_content_part_url({'type': 'video_url'}) is None
        assert get_media_content_part_url({'type': 'video_url', 'video_url': 'file-id-1'}) is None

    def test_missing_url(self):
        assert get_media_content_part_url({'type': 'video_url', 'video_url': {}}) == ('video_url', '')

    def test_non_dict(self):
        assert get_media_content_part_url(None) is None
        assert get_media_content_part_url('video_url') is None


class TestIsInlineMediaDataUrl:
    def test_video_data_url(self):
        assert is_inline_media_data_url('video_url', 'data:video/mp4;base64,AAAA') is True

    def test_image_data_url(self):
        assert is_inline_media_data_url('image_url', 'data:image/png;base64,AAAA') is True

    def test_file_id_is_not_inline(self):
        assert is_inline_media_data_url('video_url', 'file-id-1') is False

    def test_mismatched_media_kind_is_not_inline(self):
        # An image data URL must not be treated as an already-resolved video.
        assert is_inline_media_data_url('video_url', 'data:image/png;base64,AAAA') is False

    def test_unknown_part_type(self):
        assert is_inline_media_data_url('audio_url', 'data:audio/wav;base64,AAAA') is False
