// Detect the image MIME type from a file's magic bytes.
//
// Some sources hand over images without a MIME type: macOS Photos exposes its
// items under the custom UTI `com.apple.photos.item`, and browsers surface the
// dragged file with an empty `type` and an extension-less name (e.g. "photo").
// Sniffing the first bytes lets those files take the image path instead of
// being uploaded as opaque documents.

const HEIF_BRANDS = new Set(['heic', 'heif', 'heix', 'heis', 'heim', 'mif1', 'mif2', 'msf1', 'hevc']);

const chars = (bytes: Uint8Array, offset: number, length: number) =>
	String.fromCharCode(...bytes.slice(offset, offset + length));

export const sniffImageMime = async (file: File): Promise<string | null> => {
	try {
		const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
		if (bytes.length < 12) {
			return null;
		}

		if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
			return 'image/jpeg';
		}
		if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
			return 'image/png';
		}
		if (bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x38) {
			return 'image/gif';
		}
		if (chars(bytes, 0, 4) === 'RIFF' && chars(bytes, 8, 4) === 'WEBP') {
			return 'image/webp';
		}
		if (chars(bytes, 4, 4) === 'ftyp' && HEIF_BRANDS.has(chars(bytes, 8, 4))) {
			return 'image/heic';
		}
		if (bytes[0] === 0x42 && bytes[1] === 0x4d) {
			return 'image/bmp';
		}

		return null;
	} catch {
		return null;
	}
};

// Returns a copy of the file with the sniffed MIME type when the declared type
// is missing or non-image. Files that already identify as images pass through
// unchanged.
export const withDetectedImageMime = async (file: File): Promise<File> => {
	const declaredType = (file.type ?? '').split(';')[0].trim().toLowerCase();
	if (declaredType.startsWith('image/')) {
		return file;
	}

	const detected = await sniffImageMime(file);
	if (!detected) {
		return file;
	}

	const extension = detected === 'image/jpeg' ? 'jpg' : detected.split('/')[1];
	const name = /\.(?:[a-z0-9]+)$/i.test(file.name) ? file.name : `${file.name}.${extension}`;
	return new File([file], name, { type: detected });
};
