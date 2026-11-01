/**
 * Sniff the MIME type of image files from their magic bytes.
 *
 * Some drag-and-drop sources hand over images without a usable MIME type or
 * file extension. macOS Photos exposes its items under the custom UTI
 * `com.apple.photos.item`, and browsers surface the dragged file with an
 * empty `type` and an extension-less name (e.g. `photo`). Without the magic
 * bytes there is no way to tell such a file is an image, so callers that route
 * uploads on `file.type` misclassify it.
 */

// ISO base media (MP4) container major brands, read from the `ftyp` box at
// offset 8. Anything not in one of these sets is treated as non-image (a video
// or other MP4 payload) and left to the normal document path.
const AVIF_BRANDS = new Set(['avif', 'avis']);
const HEIF_BRANDS = new Set([
	'heic',
	'heix',
	'heim',
	'heis',
	'hevc',
	'hevx',
	'mif1',
	'mheix',
	'mheis',
	'heif'
]);

const MIME_TO_EXTENSION: Record<string, string> = {
	'image/jpeg': 'jpg',
	'image/png': 'png',
	'image/gif': 'gif',
	'image/webp': 'webp',
	'image/heic': 'heic',
	'image/heif': 'heif',
	'image/avif': 'avif',
	'image/bmp': 'bmp',
	'image/tiff': 'tif'
};

/**
 * Return the image MIME type detected from the file's leading bytes, or `null`
 * when the content does not identify as a known image format.
 */
export async function sniffImageMime(file: File): Promise<string | null> {
	const head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
	if (head.length < 12) {
		return null;
	}

	const str = (offset: number, length: number) =>
		String.fromCharCode(...head.slice(offset, offset + length));

	// RIFF container: identify the payload by its format tag.
	if (str(0, 4) === 'RIFF') {
		return str(8, 4) === 'WEBP' ? 'image/webp' : null;
	}

	// ISO base media container: read the major brand from the `ftyp` box.
	if (str(4, 4) === 'ftyp') {
		const brand = str(8, 4);
		if (AVIF_BRANDS.has(brand)) {
			return 'image/avif';
		}
		if (HEIF_BRANDS.has(brand)) {
			return 'image/heif';
		}
		return null;
	}

	if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) {
		return 'image/jpeg';
	}
	if (
		head[0] === 0x89 &&
		head[1] === 0x50 &&
		head[2] === 0x4e &&
		head[3] === 0x47
	) {
		return 'image/png';
	}
	if (str(0, 6) === 'GIF87a' || str(0, 6) === 'GIF89a') {
		return 'image/gif';
	}
	if (head[0] === 0x42 && head[1] === 0x4d) {
		return 'image/bmp';
	}

	// TIFF (little- and big-endian byte order markers).
	if (str(0, 2) === 'II' && head[2] === 0x2a && head[3] === 0x00) {
		return 'image/tiff';
	}
	if (str(0, 2) === 'MM' && head[2] === 0x00 && head[3] === 0x2a) {
		return 'image/tiff';
	}

	return null;
}

/**
 * Given a dropped or pasted file, return a usable `File` for image handling.
 *
 * If the file already declares an `image/*` MIME type it is returned
 * unchanged. Otherwise the content is sniffed; when an image is detected the
 * file is re-wrapped with the detected MIME type and, when the name has no
 * extension, with an appropriate one. Non-image files are returned unchanged
 * so the existing document path can handle them.
 */
export async function withDetectedImageMime(file: File): Promise<File> {
	if (file.type?.startsWith('image/')) {
		return file;
	}

	const detected = await sniffImageMime(file);
	if (!detected) {
		return file;
	}

	const hasExtension = /\.[A-Za-z0-9]+$/.test(file.name);
	const name = hasExtension
		? file.name
		: `${file.name || 'image'}.${MIME_TO_EXTENSION[detected] ?? 'img'}`;

	return new File([file], name, { type: detected });
}
