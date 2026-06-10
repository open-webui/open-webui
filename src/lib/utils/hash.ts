/**
 * Compute SHA-256 checksum of a File.
 *
 * Uses the Web Crypto API when available (HTTPS / localhost).
 * Falls back to a pure-JS implementation for plain HTTP deployments
 * where crypto.subtle is unavailable.
 *
 * @returns lowercase hex-encoded SHA-256 digest
 */
export async function computeFileHash(file: File): Promise<string> {
	const buffer = await file.arrayBuffer();

	if (globalThis.crypto?.subtle) {
		const digest = await crypto.subtle.digest('SHA-256', buffer);
		return hexEncode(new Uint8Array(digest));
	}

	return sha256Fallback(new Uint8Array(buffer));
}

function hexEncode(bytes: Uint8Array): string {
	const hex: string[] = new Array(bytes.length);
	for (let i = 0; i < bytes.length; i++) {
		hex[i] = bytes[i].toString(16).padStart(2, '0');
	}
	return hex.join('');
}

// ── Pure-JS SHA-256 (RFC 6234) ──────────────────────────────────────────────
// Used only when crypto.subtle is unavailable (HTTP deployments).

const K: Uint32Array = new Uint32Array([
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]);

function rotr(n: number, x: number): number {
	return (x >>> n) | (x << (32 - n));
}

function sha256Fallback(data: Uint8Array): string {
	// Pre-processing: padding
	const bitLen = data.length * 8;
	const padLen = (((data.length + 8) >>> 6) + 1) << 6;
	const padded = new Uint8Array(padLen);
	padded.set(data);
	padded[data.length] = 0x80;

	// Append original length in bits as 64-bit big-endian
	const view = new DataView(padded.buffer);
	view.setUint32(padLen - 4, bitLen, false);

	// Initial hash values
	let h0 = 0x6a09e667;
	let h1 = 0xbb67ae85;
	let h2 = 0x3c6ef372;
	let h3 = 0xa54ff53a;
	let h4 = 0x510e527f;
	let h5 = 0x9b05688c;
	let h6 = 0x1f83d9ab;
	let h7 = 0x5be0cd19;

	const w = new Uint32Array(64);

	for (let offset = 0; offset < padLen; offset += 64) {
		// Prepare message schedule
		for (let i = 0; i < 16; i++) {
			w[i] = view.getUint32(offset + i * 4, false);
		}
		for (let i = 16; i < 64; i++) {
			const s0 = rotr(7, w[i - 15]) ^ rotr(18, w[i - 15]) ^ (w[i - 15] >>> 3);
			const s1 = rotr(17, w[i - 2]) ^ rotr(19, w[i - 2]) ^ (w[i - 2] >>> 10);
			w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
		}

		let a = h0,
			b = h1,
			c = h2,
			d = h3;
		let e = h4,
			f = h5,
			g = h6,
			h = h7;

		for (let i = 0; i < 64; i++) {
			const S1 = rotr(6, e) ^ rotr(11, e) ^ rotr(25, e);
			const ch = (e & f) ^ (~e & g);
			const temp1 = (h + S1 + ch + K[i] + w[i]) | 0;
			const S0 = rotr(2, a) ^ rotr(13, a) ^ rotr(22, a);
			const maj = (a & b) ^ (a & c) ^ (b & c);
			const temp2 = (S0 + maj) | 0;

			h = g;
			g = f;
			f = e;
			e = (d + temp1) | 0;
			d = c;
			c = b;
			b = a;
			a = (temp1 + temp2) | 0;
		}

		h0 = (h0 + a) | 0;
		h1 = (h1 + b) | 0;
		h2 = (h2 + c) | 0;
		h3 = (h3 + d) | 0;
		h4 = (h4 + e) | 0;
		h5 = (h5 + f) | 0;
		h6 = (h6 + g) | 0;
		h7 = (h7 + h) | 0;
	}

	const result = new Uint8Array(32);
	const out = new DataView(result.buffer);
	out.setUint32(0, h0, false);
	out.setUint32(4, h1, false);
	out.setUint32(8, h2, false);
	out.setUint32(12, h3, false);
	out.setUint32(16, h4, false);
	out.setUint32(20, h5, false);
	out.setUint32(24, h6, false);
	out.setUint32(28, h7, false);

	return hexEncode(result);
}
