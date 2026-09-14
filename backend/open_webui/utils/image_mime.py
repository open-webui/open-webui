def detect_image_mime_type(img_data: bytes) -> str:
    """Infer an image MIME type from magic bytes.

    Bare ``b64_json`` payloads carry no format metadata, so the file store
    must sniff the decoded bytes instead of assuming PNG.
    """
    if img_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if img_data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if len(img_data) >= 12 and img_data.startswith(b'RIFF') and img_data[8:12] == b'WEBP':
        return 'image/webp'
    if img_data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    return 'image/png'
