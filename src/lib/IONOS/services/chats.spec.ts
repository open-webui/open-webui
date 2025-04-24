import { describe, beforeAll, afterAll, beforeEach, expect, it, vi } from 'vitest';
import { type Writable, get, writable } from 'svelte/store';
import type { Chat } from '$lib/apis/chats/types';
import {
	EXPORT_FILENAME_PREFIX,
	deleteAll,
	exportAll,
	hasChats,
} from './chats';

const mocks = vi.hoisted(() => {
	return {
		appNavigation: {
			goto: vi.fn(),
		},
		stores: {
			// x xts-expect-error
			chats: { } as Writable<Chat[]>,
		},
		api: {
			chats: {
				deleteAllChats: vi.fn(),
				getAllChats: vi.fn(),
				getChatList: vi.fn(),
			},
		},
		fileSaver: vi.fn(),
	};
});

vi.mock('$app/navigation', async () => {
	return {
		goto: mocks.appNavigation.goto,
	};
});

vi.mock('$lib/stores', async () => {
	mocks.stores.chats = writable([]);

	return {
		chats: mocks.stores.chats,
	};
});

vi.mock('$lib/apis/chats', async () => {
	return {
		deleteAllChats: mocks.api.chats.deleteAllChats,
		getAllChats: mocks.api.chats.getAllChats,
		getChatList: mocks.api.chats.getChatList,
	};
});

vi.mock('file-saver', async () => {
	return {
		default: mocks.fileSaver,
	};
});

vi.stubGlobal('localStorage', { });

describe('chats', () => {
	const mockToken = 'sometoken';

	beforeEach(() => {
		vi.resetAllMocks();

		localStorage.token = mockToken;

		mocks.appNavigation.goto.mockImplementation(() => Promise.resolve());

		mocks.api.chats.deleteAllChats.mockImplementation(() => Promise.resolve());
		mocks.api.chats.getAllChats.mockImplementation(() => Promise.resolve([]));
		mocks.api.chats.getChatList.mockImplementation(() => Promise.resolve([]));

		mocks.fileSaver.mockImplementation(() => { });
	});

	describe('deleteAll()', () => {
		beforeEach(() => {
			mocks.stores.chats.set([]);
		});

		it("should first navigate to /", async () => {
			await deleteAll();
			expect(mocks.appNavigation.goto).toHaveBeenCalledWith('/');
		});

		it("should call api deleteAllChats() with the token from localStorage", async () => {
			await deleteAll();
			expect(mocks.api.chats.deleteAllChats).toHaveBeenCalledWith(mockToken);
		});

		describe("deleteAllChats() failed", () => {
			beforeEach(() => {
				mocks.api.chats.deleteAllChats.mockImplementation(() => Promise.reject(new Error('call failed')));
			});

			it('should not call getChatList()', async () => {
				await expect(deleteAll()).rejects.toThrow('call failed');
				expect(mocks.api.chats.getChatList).not.toHaveBeenCalled();
			});

			it("should reject with the error", async () => {
				await expect(deleteAll()).rejects.toThrow('call failed');
			});
		});

		describe("deleteAllChats() successful", () => {
			const mockChatsPostDelete: Chat[] = [
				{ id: 'id-987', title: 'foo postdelete', updated_at: 47, created_at: 47 },
			];

			beforeEach(() => {
				mocks.api.chats.getChatList.mockImplementation(() => Promise.resolve(mockChatsPostDelete));
			});

			it("should call getChatList() with token, 1", async () => {
				await deleteAll();
				expect(mocks.api.chats.getChatList).toHaveBeenCalledWith(mockToken, 1);
			});

			it('should set the chats store to the result of getChatList()', async () => {
				const mockChatsPreDelete: Chat[] = [
					{ id: 'id-123', title: 'foo predelete', updated_at: 47, created_at: 47 },
				];
				mocks.stores.chats.set(mockChatsPreDelete);
				await deleteAll();
				expect(get(mocks.stores.chats)).toEqual(mockChatsPostDelete);
			});
		});
	});

	describe('export()', () => {
		beforeAll(() => {
			vi.useFakeTimers();
			vi.setSystemTime(0);
		});

		afterAll(() => {
			vi.useRealTimers();
		});

		it("should call getAllChats() with token", async () => {
			await exportAll();
			expect(mocks.api.chats.getAllChats).toHaveBeenCalledWith(mockToken);
		});

		describe("getAllChats() failed", () => {
			beforeEach(() => {
				mocks.api.chats.getAllChats.mockImplementation(() => Promise.reject(new Error('call failed')));
			});

			it('should not file-saver', async () => {
				await expect(exportAll()).rejects.toThrow('call failed');
				expect(mocks.fileSaver).not.toHaveBeenCalled();
			});

			it("should reject with the error", async () => {
				await expect(exportAll()).rejects.toThrow('call failed');
			});
		});

		describe("getAllChats() successful", async () => {
			it('should pass the result as JSON string wrapped in a Blob to file-saver', async () => {
				const mockChats = [{ id: 'foo' }];
				mocks.api.chats.getAllChats.mockImplementation(() => Promise.resolve(mockChats));
				await exportAll();
				expect(mocks.fileSaver).toHaveBeenCalled();
				const [ blob ] = mocks.fileSaver.mock.calls[0];
				const content = await blob.text();
				expect(blob.type).toEqual('application/json');
				expect(content).toEqual(JSON.stringify(mockChats));
			});

			it("should call file-saver with a prefix and the current time as filename", async () => {
				await exportAll();
				expect(mocks.fileSaver).toHaveBeenCalled();
				const [, filename] = mocks.fileSaver.mock.calls[0];
				expect(filename).toEqual(`${EXPORT_FILENAME_PREFIX}-1970-01-01--00-00.json`);
			});
		});
	});

	describe('hasChats()', () => {
		it("should call getChatList() with token, 1", async () => {
			await hasChats();
			expect(mocks.api.chats.getChatList).toHaveBeenCalledWith(mockToken, 1);
		});

		it('should return false if the user has no chats', async () => {
			mocks.api.chats.getChatList.mockImplementation(() => Promise.resolve([]));
			expect(await hasChats()).toBe(false);
		});

		it('should return true if the user has one or more chats', async () => {
			mocks.api.chats.getChatList.mockImplementation(() => Promise.resolve([
				{ id: 'foo' },
			]));
			expect(await hasChats()).toBe(true);

			mocks.api.chats.getChatList.mockImplementation(() => Promise.resolve([
				{ id: 'foo' },
				{ id: 'bar' },
			]));
			expect(await hasChats()).toBe(true);
		});
	});
});
