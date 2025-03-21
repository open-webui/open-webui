import type { KnowledgeFile } from '$lib/apis/knowledge/types';
import { describe, afterEach, expect, it, vi } from 'vitest'
import { upload, init, files } from './uploader';

const mocks = vi.hoisted(() => {
	return {
		addFile: vi.fn(),
	}
});

vi.mock('$lib/IONOS/services/knowledge', async () => {
	return {
		addFile: mocks.addFile,
	};
});

class FileMock extends File {
	constructor(fileBits: ArrayBuffer[], fileName: string) {
		const blobs = fileBits.map((arrayBuffer) => new Blob([arrayBuffer]));
		super(blobs, fileName);
	}
}

describe('uploader', () => {
	afterEach(() => {
		init([]);
	});

	it('shoud set files on init()', () => {
		vi.spyOn(files, 'set');
		const knowledgeFileMocks: KnowledgeFile[] = [
			// @ts-expect-error Type '{ id: string; }' is missing the following properties from type 'KnowledgeFile': created_at, data, filename, hash, and 3 more.
			{ id: '47-1' },
			// @ts-expect-error Type '{ id: string; }' is missing the following properties from type 'KnowledgeFile': created_at, data, filename, hash, and 3 more.
			{ id: '47-2' },
		];
		init(knowledgeFileMocks)
		expect(files.set).toHaveBeenCalledWith(knowledgeFileMocks);
	});

	it('should call addFile() and set files with each file', async () => {
		init([]);
		vi.spyOn(files, 'set');
		const filesSet = vi.mocked(files.set);

		const knowledgeId = 'foo-knowledge-47';
		const domFiles: File[] = [
			new FileMock([new ArrayBuffer(0)], 'foo'),
			new FileMock([new ArrayBuffer(0)], 'foo'),
		];

		const knowledgeFileMocks: KnowledgeFile[] = [];
		let id = 0;
		mocks.addFile.mockImplementation(async () => {
			id++;
			knowledgeFileMocks.push({ id: String(id) } as KnowledgeFile);
			return [...knowledgeFileMocks];
		});

		await upload(knowledgeId, domFiles);

		expect(mocks.addFile).toHaveBeenCalledWith(knowledgeId, domFiles[0]);
		expect(mocks.addFile).toHaveBeenCalledWith(knowledgeId, domFiles[1]);
		expect(filesSet).toHaveBeenCalledTimes(2);
		expect(filesSet.mock.calls[0][0]).toEqual([knowledgeFileMocks[0]]);
		expect(filesSet.mock.calls[1][0]).toEqual([knowledgeFileMocks[0], knowledgeFileMocks[1]]);
	});
});
