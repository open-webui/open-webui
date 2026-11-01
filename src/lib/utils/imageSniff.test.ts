import { describe, expect, it } from 'vitest';
import { sniffImageMime, withDetectedImageMime } from './imageSniff';

const fileFromBytes = (bytes: Uint8Array, name = 'photo', type = '') =>
	new File([bytes as BlobPart], name, { type });

// First 12 bytes of real container headers (padded with zeros).
const ascii = (s: string, padTo = 12) =>
	new Uint8Array([
		...[...s].map((c) => c.charCodeAt(0)),
		...Array(padTo - s.length).fill(0)
	]);

const headers: Record<string, Uint8Array> = {
	jpeg: new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0, 0, 0, 0, 0]),
	png: new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]),
	gif87a: ascii('GIF87a'),
	gif89a: ascii('GIF89a'),
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
	heif: new Uint8Array([
		0, 0, 0, 0x18,
		0x66, 0x74, 0x79, 0x70, // ftyp
		0x68, 0x65, 0x69, 0x66 // heif
	]),
	avif: new Uint8Array([
		0, 0, 0, 0x18,
		0x66, 0x74, 0x79, 0x70, // ftyp
		0x61, 0x76, 0x69, 0x66 // avif
	]),
	bmp: new Uint8Array([0x42, 0x4d, 0x36, 0xfc, 0, 0, 0, 0, 0, 0, 0, 0]),
	tiffLe: new Uint8Array([0x49, 0x49, 0x2a, 0x00, 0, 0, 0, 0, 0, 0, 0, 0]),
	tiffBe: new Uint8Array([0x4d, 0x4d, 0x00, 0x2a, 0, 0, 0, 0, 0, 0, 0, 0]),
	pdf: new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0, 0, 0, 0]),
	// An MP4 video container (ftyp with a non-image brand) must not be an image.
	mp4Video: new Uint8Array([
		0, 0, 0, 0x18,
		0x66, 0x74, 0x79, 0x70, // ftyp
		0x69, 0x73, 0x6f, 0x6d // isom
	])
};

describe('sniffImageMime', () => {
	it.each([
		['jpeg', 'image/jpeg'],
		['png', 'image/png'],
		['gif87a', 'image/gif'],
		['gif89a', 'image/gif'],
		['webp', 'image/webp'],
		['heic', 'image/heif'],
		['heif', 'image/heif'],
		['avif', 'image/avif'],
		['bmp', 'image/bmp'],
		['tiffLe', 'image/tiff'],
		['tiffBe', 'image/tiff']
	])('detects %s', async (name, expected) => {
		expect(await sniffImageMime(fileFromBytes(headers[name]))).toBe(expected);
	});

	it('returns null for non-image content', async () => {
		expect(await sniffImageMime(fileFromBytes(headers.pdf))).toBeNull();
	});

	it('does not treat an MP4 video container as an image', async () => {
		expect(await sniffImageMime(fileFromBytes(headers.mp4Video))).toBeNull();
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

	it('detects an AVIF with no MIME type and adds an extension', async () => {
		const result = await withDetectedImageMime(fileFromBytes(headers.avif, 'photo'));
		expect(result.type).toBe('image/avif');
		expect(result.name).toBe('photo.avif');
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

	it('passes an extension-less non-image through unchanged', async () => {
		const input = fileFromBytes(headers.mp4Video, 'clip');
		expect(await withDetectedImageMime(input)).toBe(input);
	});
});
