import base64
import unittest

from open_webui.utils.image_mime import detect_image_mime_type


PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 8
WEBP = b'RIFF' + b'\x00\x00\x00\x00' + b'WEBP' + b'\x00' * 4
GIF = b'GIF89a' + b'\x00' * 8
UNKNOWN = b'not-an-image'


class DetectImageMimeTypeTest(unittest.TestCase):
    def test_magic_bytes(self):
        self.assertEqual(detect_image_mime_type(PNG), 'image/png')
        self.assertEqual(detect_image_mime_type(JPEG), 'image/jpeg')
        self.assertEqual(detect_image_mime_type(WEBP), 'image/webp')
        self.assertEqual(detect_image_mime_type(GIF), 'image/gif')
        self.assertEqual(detect_image_mime_type(UNKNOWN), 'image/png')


class GetImageDataBareB64MimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_bare_b64_json_sniffs_jpeg(self):
        # Import lazily so the helper unit tests above still run if router
        # deps are unavailable in a minimal environment.
        from open_webui.routers.images import get_image_data

        payload = base64.b64encode(JPEG).decode('ascii')
        img_data, mime_type = await get_image_data(payload)
        self.assertEqual(img_data, JPEG)
        self.assertEqual(mime_type, 'image/jpeg')

    async def test_bare_b64_json_sniffs_webp(self):
        from open_webui.routers.images import get_image_data

        payload = base64.b64encode(WEBP).decode('ascii')
        img_data, mime_type = await get_image_data(payload)
        self.assertEqual(img_data, WEBP)
        self.assertEqual(mime_type, 'image/webp')

    async def test_bare_b64_json_fallback_png(self):
        from open_webui.routers.images import get_image_data

        payload = base64.b64encode(UNKNOWN).decode('ascii')
        img_data, mime_type = await get_image_data(payload)
        self.assertEqual(img_data, UNKNOWN)
        self.assertEqual(mime_type, 'image/png')


if __name__ == '__main__':
    unittest.main()
