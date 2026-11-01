import { describe, expect, it } from 'vitest';
import { sniffImageMime, withDetectedImageMime } from './imageSniff';

const fileFromBytes = (bytes: Uint8Array, name = 'photo', type = '') =>
	new File([bytes], name, { type });

// First 12 bytes of real container headers (padded with zeros).
const headers = {
	jpeg: new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0, 0, 0, 0, 0]),
	png: new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]),
	gif: new Uint8Array([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0, 0, 0, 0, 0, 0]),
	webp: new Uint8Array([
		0x52, 0x49, 0x46, 0x46, // RIFF
		0x24, 0, 0, 0,
		0x57, 0x45, 0x42, 0x50 // WEBP
	]),
	heic: new Uint8Array([
		0, 0, 0, 0x18,
		0x66, 0x74, 0x79, 0x70, // ftyp
		0x68, 0x65, 0x69, 0x63 // heic
	]),
	bmp: new Uint8Array([0x42, 0x4d, 0x36, 0xfc, 0, 0, 0, 0, 0, 0, 0, 0]),
	pdf: new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0, 0, 0, 0])
};

describe('sniffImageMime', () => {
	it.each([
		['jpeg', 'image/jpeg'],
		['png', 'image/png'],
		['gif', 'image/gif'],
		['webp', 'image/webp'],
		['heic', 'image/heic'],
		['bmp', 'image/bmp']
	])('detects %s', async (name, expected) => {
		expect(await sniffImageMime(fileFromBytes(headers[name]))).toBe(expected);
	});

	it('returns null for non-image content', async () => {
		expect(await sniffImageMime(fileFromBytes(headers.pdf))).toBeNull();
	});

	it('returns null for a short file', async () => {
		expect(await sniffImageMime(fileFromBytes(new Uint8Array([0xff, 0xd8])))).toBeNull();
	});
});

describe('withDetectedImageMime', () => {
	it('detects an image with no MIME type and adds an extension', async () => {
		const result = await withDetectedImageMime(fileFromBytes(headers.jpeg, 'photo'));
		expect(result.type).toBe('image/jpeg');
		expect(result.name).toBe('photo.jpg');
	});

	it('detects an image with no MIME type but keeps an existing extension', async () => {
		const result = await withDetectedImageMime(fileFromBytes(headers.png, 'photo.png'));
		expect(result.type).toBe('image/png');
		expect(result.name).toBe('photo.png');
	});

	it('passes a typed image through unchanged', async () => {
		const input = fileFromBytes(headers.jpeg, 'photo.jpg', 'image/jpeg');
		expect(await withDetectedImageMime(input)).toBe(input);
	});

	it('passes a non-image document through unchanged', async () => {
		const input = fileFromBytes(headers.pdf, 'report.pdf', 'application/pdf');
		expect(await withDetectedImageMime(input)).toBe(input);
	});
});
