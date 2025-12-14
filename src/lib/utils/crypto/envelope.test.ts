import { beforeAll, describe, expect, it } from 'vitest';

import {
	decryptChatContent,
	decryptSharePayload,
	encryptChatContent,
	encryptSharePayload,
	generateShareKey,
	importShareKey
} from './envelope';

beforeAll(async () => {
	if (!globalThis.crypto?.subtle) {
		const { webcrypto } = await import('crypto');
		(globalThis as any).crypto = webcrypto;
	}
});

describe('chat encryption envelope', () => {
	it('round-trips chat content', async () => {
		const crypto = globalThis.crypto;
		const umk = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
			'encrypt',
			'decrypt'
		]);

		const chatId = '00000000-0000-4000-8000-000000000001';
		const userId = '00000000-0000-4000-8000-000000000002';
		const content = { messages: [{ role: 'user', content: 'hello' }], history: { currentId: 'x' } };

		const encrypted = await encryptChatContent(umk, chatId, userId, content);
		const decrypted = await decryptChatContent(umk, encrypted.enc, chatId, userId);

		expect(decrypted).toEqual(content);
	});

	it('fails decryption with wrong AAD', async () => {
		const crypto = globalThis.crypto;
		const umk = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
			'encrypt',
			'decrypt'
		]);

		const chatId = '00000000-0000-4000-8000-000000000001';
		const userId = '00000000-0000-4000-8000-000000000002';
		const content = { messages: [{ role: 'user', content: 'hello' }] };

		const encrypted = await encryptChatContent(umk, chatId, userId, content);

		await expect(decryptChatContent(umk, encrypted.enc, 'wrong-chat-id', userId)).rejects.toThrow();
		await expect(decryptChatContent(umk, encrypted.enc, chatId, 'wrong-user-id')).rejects.toThrow();
	});

	it('rejects unsupported encrypted chat payloads', async () => {
		const crypto = globalThis.crypto;
		const umk = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, [
			'encrypt',
			'decrypt'
		]);

		const chatId = '00000000-0000-4000-8000-000000000001';
		const userId = '00000000-0000-4000-8000-000000000002';

		await expect(decryptChatContent(umk, null as any, chatId, userId)).rejects.toThrow(
			'Unsupported encrypted chat payload'
		);
		await expect(
			decryptChatContent(umk, { v: 2 } as any, chatId, userId)
		).rejects.toThrow('Unsupported encrypted chat payload');
	});
});

describe('encrypted share packages', () => {
	it('round-trips shared payload using fragment key', async () => {
		const shareId = '00000000-0000-4000-8000-000000000010';
		const payload = { title: 'Shared chat', messages: [{ role: 'user', content: 'hello' }] };

		const { key, keyB64Url } = await generateShareKey();
		const encrypted = await encryptSharePayload(key, shareId, payload);

		const importedKey = await importShareKey(keyB64Url);
		const decrypted = await decryptSharePayload(importedKey, encrypted.share, shareId);

		expect(decrypted).toEqual(payload);
	});

	it('fails decryption with wrong share id', async () => {
		const shareId = '00000000-0000-4000-8000-000000000010';
		const payload = { ok: true };

		const { key } = await generateShareKey();
		const encrypted = await encryptSharePayload(key, shareId, payload);

		await expect(decryptSharePayload(key, encrypted.share, 'wrong-share-id')).rejects.toThrow();
	});

	it('rejects unsupported encrypted share payloads', async () => {
		const { key } = await generateShareKey();
		const shareId = '00000000-0000-4000-8000-000000000010';

		await expect(decryptSharePayload(key, null as any, shareId)).rejects.toThrow(
			'Unsupported encrypted share payload'
		);
		await expect(
			decryptSharePayload(key, { v: 2 } as any, shareId)
		).rejects.toThrow('Unsupported encrypted share payload');
	});
});
