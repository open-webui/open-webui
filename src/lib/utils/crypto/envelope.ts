import { fromB64Url, toB64Url } from './base64url';
import { getStoredUMK, setStoredUMK, type StoredUMKRecordV1 } from './idb';

type EncV1 = {
	v: 1;
	alg: 'A256GCM';
	k_alg: 'A256GCM';
	iv: string;
	ct: string;
	dek_wrap: {
		iv: string;
		ct: string;
	};
	aad: string;
};

type ShareEncV1 = {
	v: 1;
	alg: 'A256GCM';
	iv: string;
	ct: string;
	aad: string;
};

function requireCrypto(): Crypto {
	if (!globalThis.crypto?.subtle || typeof globalThis.crypto.getRandomValues !== 'function') {
		throw new Error('Web Crypto API is not available');
	}
	return globalThis.crypto;
}

function bytesToArrayBuffer(bytes: Uint8Array): ArrayBuffer {
	return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function buildAadBytes(chatId: string, userId: string): Uint8Array {
	return new TextEncoder().encode(JSON.stringify({ chat_id: chatId, user_id: userId, v: 1 }));
}

function buildShareAadBytes(shareId: string): Uint8Array {
	return new TextEncoder().encode(JSON.stringify({ share_id: shareId, v: 1 }));
}

async function fingerprintKey(key: CryptoKey): Promise<string> {
	const crypto = requireCrypto();
	const raw = await crypto.subtle.exportKey('raw', key);
	const digest = await crypto.subtle.digest('SHA-256', raw);
	return toB64Url(new Uint8Array(digest));
}

async function exportKeyJwk(key: CryptoKey): Promise<JsonWebKey> {
	const crypto = requireCrypto();
	return (await crypto.subtle.exportKey('jwk', key)) as JsonWebKey;
}

async function importKeyJwk(jwk: JsonWebKey): Promise<CryptoKey> {
	const crypto = requireCrypto();
	return crypto.subtle.importKey('jwk', jwk, { name: 'AES-GCM' }, true, ['encrypt', 'decrypt']);
}

export async function getOrCreateUMK(): Promise<{ key: CryptoKey; fingerprint: string }> {
	let record: StoredUMKRecordV1 | null = null;
	try {
		record = await getStoredUMK();
	} catch {
		record = null;
	}

	if (record) {
		try {
			const key = await importKeyJwk(record.jwk);
			const fingerprint = await fingerprintKey(key);

			if (fingerprint !== record.fingerprint) {
				await setStoredUMK({ ...record, fingerprint });
			}

			return { key, fingerprint };
		} catch {
			// fall through and create a new key
		}
	}

	const crypto = requireCrypto();
	const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
		'encrypt',
		'decrypt'
	]);
	const fingerprint = await fingerprintKey(key);
	const jwk = await exportKeyJwk(key);
	await setStoredUMK({ v: 1, jwk, fingerprint });
	return { key, fingerprint };
}

export async function encryptChatContent(
	umk: CryptoKey,
	chatId: string,
	userId: string,
	contentObj: unknown
): Promise<{ enc: EncV1 }> {
	const crypto = requireCrypto();
	const aadBytes = buildAadBytes(chatId, userId);

	const dek = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
		'encrypt',
		'decrypt'
	]);
	const dekRaw = await crypto.subtle.exportKey('raw', dek);

	const wrapIv = crypto.getRandomValues(new Uint8Array(12));
	const wrapCt = await crypto.subtle.encrypt(
		{ name: 'AES-GCM', iv: wrapIv, additionalData: aadBytes },
		umk,
		dekRaw
	);

	const plaintextBytes = new TextEncoder().encode(JSON.stringify(contentObj));
	const iv = crypto.getRandomValues(new Uint8Array(12));
	const ct = await crypto.subtle.encrypt(
		{ name: 'AES-GCM', iv, additionalData: aadBytes },
		dek,
		plaintextBytes
	);

	return {
		enc: {
			v: 1,
			alg: 'A256GCM',
			k_alg: 'A256GCM',
			iv: toB64Url(iv),
			ct: toB64Url(new Uint8Array(ct)),
			dek_wrap: {
				iv: toB64Url(wrapIv),
				ct: toB64Url(new Uint8Array(wrapCt))
			},
			aad: toB64Url(aadBytes)
		}
	};
}

export async function decryptChatContent(
	umk: CryptoKey,
	encObj: EncV1,
	chatId: string,
	userId: string
): Promise<unknown> {
	if (!encObj || encObj.v !== 1) {
		throw new Error('Unsupported encrypted chat payload');
	}

	const crypto = requireCrypto();
	const aadBytes = buildAadBytes(chatId, userId);

	const wrapIv = fromB64Url(encObj.dek_wrap.iv);
	const wrapCt = fromB64Url(encObj.dek_wrap.ct);
	const dekRaw = await crypto.subtle.decrypt(
		{ name: 'AES-GCM', iv: wrapIv, additionalData: aadBytes },
		umk,
		bytesToArrayBuffer(wrapCt)
	);

	const dek = await crypto.subtle.importKey('raw', dekRaw, { name: 'AES-GCM' }, false, [
		'encrypt',
		'decrypt'
	]);

	const iv = fromB64Url(encObj.iv);
	const ct = fromB64Url(encObj.ct);
	const plaintext = await crypto.subtle.decrypt(
		{ name: 'AES-GCM', iv, additionalData: aadBytes },
		dek,
		bytesToArrayBuffer(ct)
	);

	const plaintextStr = new TextDecoder().decode(plaintext);
	return JSON.parse(plaintextStr);
}

export async function generateShareKey(): Promise<{ key: CryptoKey; keyB64Url: string }> {
	const crypto = requireCrypto();
	const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
		'encrypt',
		'decrypt'
	]);
	const raw = await crypto.subtle.exportKey('raw', key);
	return { key, keyB64Url: toB64Url(new Uint8Array(raw)) };
}

export async function importShareKey(keyB64Url: string): Promise<CryptoKey> {
	const crypto = requireCrypto();
	const raw = fromB64Url(keyB64Url.trim());
	return crypto.subtle.importKey('raw', bytesToArrayBuffer(raw), { name: 'AES-GCM' }, false, [
		'encrypt',
		'decrypt'
	]);
}

export async function encryptSharePayload(
	shareKey: CryptoKey,
	shareId: string,
	payloadObj: unknown
): Promise<{ share: ShareEncV1 }> {
	const crypto = requireCrypto();
	const aadBytes = buildShareAadBytes(shareId);

	const plaintextBytes = new TextEncoder().encode(JSON.stringify(payloadObj));
	const iv = crypto.getRandomValues(new Uint8Array(12));
	const ct = await crypto.subtle.encrypt(
		{ name: 'AES-GCM', iv, additionalData: aadBytes },
		shareKey,
		plaintextBytes
	);

	return {
		share: {
			v: 1,
			alg: 'A256GCM',
			iv: toB64Url(iv),
			ct: toB64Url(new Uint8Array(ct)),
			aad: toB64Url(aadBytes)
		}
	};
}

export async function decryptSharePayload(
	shareKey: CryptoKey,
	shareObj: ShareEncV1,
	shareId: string
): Promise<unknown> {
	if (!shareObj || shareObj.v !== 1) {
		throw new Error('Unsupported encrypted share payload');
	}

	const crypto = requireCrypto();
	const aadBytes = buildShareAadBytes(shareId);

	const iv = fromB64Url(shareObj.iv);
	const ct = fromB64Url(shareObj.ct);
	const plaintext = await crypto.subtle.decrypt(
		{ name: 'AES-GCM', iv, additionalData: aadBytes },
		shareKey,
		bytesToArrayBuffer(ct)
	);

	const plaintextStr = new TextDecoder().decode(plaintext);
	return JSON.parse(plaintextStr);
}

export async function exportRecoveryKey(): Promise<string> {
	const { key } = await getOrCreateUMK();
	const crypto = requireCrypto();
	const raw = await crypto.subtle.exportKey('raw', key);
	return toB64Url(new Uint8Array(raw));
}

export async function importRecoveryKey(
	recoveryKeyB64Url: string
): Promise<{ fingerprint: string }> {
	const crypto = requireCrypto();
	const raw = fromB64Url(recoveryKeyB64Url.trim());
	const key = await crypto.subtle.importKey(
		'raw',
		bytesToArrayBuffer(raw),
		{ name: 'AES-GCM' },
		true,
		['encrypt', 'decrypt']
	);

	const fingerprint = await fingerprintKey(key);
	const jwk = await exportKeyJwk(key);
	await setStoredUMK({ v: 1, jwk, fingerprint });
	return { fingerprint };
}
