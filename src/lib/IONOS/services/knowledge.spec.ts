import { describe, beforeEach, afterEach, expect, it, vi } from 'vitest';
import {
	create,
	remove,
	removeFile,
	addFile,
} from './knowledge';

const mocks = vi.hoisted(() => {
	return {
		knowledge: {
			createNewKnowledge: vi.fn(),
			deleteKnowledgeById: vi.fn(),
			addFileToKnowledgeById: vi.fn(),
			removeFileFromKnowledgeById: vi.fn(),
		},
		files: {
			uploadFile: vi.fn(),
		},
	};
});

vi.mock('$lib/apis/files', async () => {
	return {
		uploadFile: mocks.files.uploadFile,
	};
});

vi.mock('$lib/apis/knowledge', async () => {
	return {
		createNewKnowledge: mocks.knowledge.createNewKnowledge,
		deleteKnowledgeById: mocks.knowledge.deleteKnowledgeById,
		addFileToKnowledgeById: mocks.knowledge.addFileToKnowledgeById,
		removeFileFromKnowledgeById: mocks.knowledge.removeFileFromKnowledgeById,
	};
});

describe('knowledge', () => {
	const mockToken = 'mock-token';
	let originalLocalStorage: Storage;

	beforeEach(() => {
		originalLocalStorage = global.localStorage as unknown as Storage;
		global.localStorage = global.localStorage ?? ({ } as unknown as Storage);
		global.localStorage.token = mockToken;
	});

	afterEach(() => {
		global.localStorage = originalLocalStorage;
		vi.clearAllMocks();
	});

	describe('create()', () => {
		it('should call createNewKnowledge() with token, name, description', async () => {
			await create('Test Knowledge', 'Test Description').catch(() => { });
			expect(mocks.knowledge.createNewKnowledge).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.createNewKnowledge).toHaveBeenCalledWith(
				mockToken,
				'Test Knowledge',
				'Test Description',
				{
					read: { group_ids: [] },
					write: { group_ids: [] },
				}
			);
		});

		it('should fail on empty name', async () => {
			await expect(create('', 'Test Description')).rejects.toThrow('The fields name and description may not be empty');
		});

		it('should fail on empty description', async () => {
			await expect(create('Test Knowledge', '')).rejects.toThrow('The fields name and description may not be empty');
		});

		it('should fail if createNewKnowledge() rejects', async () => {
			mocks.knowledge.createNewKnowledge.mockRejectedValueOnce(new Error('Mock error'));
			await expect(create('Test Knowledge', 'Test Description')).rejects.toThrow('Exception while creating knowledge: Error: Mock error');
		});

		it('should fail if createNewKnowledge() resolves with empty result', async () => {
			mocks.knowledge.createNewKnowledge.mockResolvedValueOnce(undefined);
			await expect(create('Test Knowledge', 'Test Description')).rejects.toThrow('Error creating knowledge');
		});

		it('should return the result of createNewKnowledge() if it resolves with a knowledge object', async () => {
			const knowledge = {
				id: 'test-id',
				user_id: 'test-user-id',
				name: 'Test Knowledge',
				description: 'Test Description',
				data: null,
				access_control: { read: { group_ids: [] }, write: { group_ids: [] } },
				created_at: 1643723900,
				updated_at: 1643723900,
				files: null,
			};

			mocks.knowledge.createNewKnowledge.mockResolvedValueOnce(knowledge);
			await create('Test Knowledge', 'Test Description');
			expect(mocks.knowledge.createNewKnowledge).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.createNewKnowledge).toHaveBeenCalledWith(
				mockToken,
				'Test Knowledge',
				'Test Description',
				{
					read: { group_ids: [] },
					write: { group_ids: [] },
				}
			);
		});
	});

	describe('remove()', () => {
		it('should call deleteKnowledgeById() with token, knowledge ID', async () => {
			await remove('test-knowledge-id').catch(() => { });
			expect(mocks.knowledge.deleteKnowledgeById).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.deleteKnowledgeById).toHaveBeenCalledWith(mockToken, 'test-knowledge-id');
		});

		it('should fail if deleteKnowledgeById() rejects', async () => {
			mocks.knowledge.deleteKnowledgeById.mockRejectedValueOnce(new Error('Mock error'));
			await expect(remove('test-knowledge-id')).rejects.toThrow('Exception while deleting knowledge: Error: Mock error');
		});

		it('should fail if deleteKnowledgeById() resolves with false', async () => {
			mocks.knowledge.deleteKnowledgeById.mockResolvedValueOnce(false);
			await expect(remove('test-knowledge-id')).rejects.toThrow('Error deleting knowledge');
		});

		it('should return the result of deleteKnowledgeById() if it resolves with true', async () => {
			mocks.knowledge.deleteKnowledgeById.mockResolvedValueOnce(true);
			await remove('test-knowledge-id');
			expect(mocks.knowledge.deleteKnowledgeById).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.deleteKnowledgeById).toHaveBeenCalledWith(mockToken, 'test-knowledge-id');
		});
	});

	describe('removeFile()', () => {
		it('should call removeFileFromKnowledgeById() with token, knowledge ID, file ID', async () => {
			await removeFile('test-knowledge-id', 'test-file-id').catch(() => { });
			expect(mocks.knowledge.removeFileFromKnowledgeById).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.removeFileFromKnowledgeById).toHaveBeenCalledWith(mockToken, 'test-knowledge-id', 'test-file-id');
		});

		it('should fail if removeFileFromKnowledgeById() rejects', async () => {
			mocks.knowledge.removeFileFromKnowledgeById.mockRejectedValueOnce(new Error('Mock error'));
			await expect(removeFile('test-knowledge-id', 'test-file-id')).rejects.toThrow('Exception while error deleting file: Error: Mock error');
		});

		it('should fail if removeFileFromKnowledgeById() resolves with empty result', async () => {
			mocks.knowledge.removeFileFromKnowledgeById.mockResolvedValueOnce(undefined);
			await expect(removeFile('test-knowledge-id', 'test-file-id')).rejects.toThrow('Error deleting file with file=test-file-id knowledge=test-knowledge-id');
		});

		it('should return the result of removeFileFromKnowledgeById() if it resolves with a knowledge object', async () => {
			const knowledge = {
				id: 'test-id',
				user_id: 'test-user-id',
				name: 'Test Knowledge',
				description: 'Test Description',
				data: null,
				access_control: { read: { group_ids: [] }, write: { group_ids: [] } },
				created_at: 1643723900,
				updated_at: 1643723900,
				files: null,
			};

			mocks.knowledge.removeFileFromKnowledgeById.mockResolvedValueOnce(knowledge);
			await removeFile('test-knowledge-id', 'test-file-id');
			expect(mocks.knowledge.removeFileFromKnowledgeById).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.removeFileFromKnowledgeById).toHaveBeenCalledWith(mockToken, 'test-knowledge-id', 'test-file-id');
		});
	});

	describe('addFile()', () => {
		it('should call uploadFile() with token, file', async () => {
			const file = new File(['test file content'], 'test-file.txt');
			await addFile('test-knowledge-id', file).catch(() => { });
			expect(mocks.files.uploadFile).toHaveBeenCalledTimes(1);
			expect(mocks.files.uploadFile).toHaveBeenCalledWith(mockToken, file);
		});

		it('should fail if uploadFile() rejects', async () => {
			mocks.files.uploadFile.mockRejectedValueOnce(new Error('Mock error'));
			const file = new File(['test file content'], 'test-file.txt');
			await expect(addFile('test-knowledge-id', file)).rejects.toThrow('Exception while uploading file: Error: Mock error');
		});

		it('should fail if uploadFile() resolves with empty result', async () => {
			mocks.files.uploadFile.mockResolvedValueOnce(undefined);
			const file = new File(['test file content'], 'test-file.txt');
			await expect(addFile('test-knowledge-id', file)).rejects.toThrow('Error uploading file');
		});

		it('should call addFileToKnowledgeById() with the file ID returned by uploadFile()', async () => {
			const file = new File(['test file content'], 'test-file.txt');
			const uploadedFile = {
				created_at: 1643723900,
				data: null,
				filename: 'test-file.txt',
				hash: 'test-hash',
				id: 'test-file-id',
				meta: {
					collection_name: 'test-collection',
					content_type: 'text/plain',
					name: 'test-file.txt',
					size: 16,
				},
				updated_at: 1643723900,
				user_id: 'test-user-id',
			};

			mocks.files.uploadFile.mockResolvedValueOnce(uploadedFile);
			await addFile('test-knowledge-id', file).catch(() => { });
			expect(mocks.knowledge.addFileToKnowledgeById).toHaveBeenCalledTimes(1);
			expect(mocks.knowledge.addFileToKnowledgeById).toHaveBeenCalledWith(mockToken, 'test-knowledge-id', 'test-file-id');
		});

		it('should fail if addFileToKnowledgeById() rejects', async () => {
			mocks.files.uploadFile.mockResolvedValueOnce({
				created_at: 1643723900,
				data: null,
				filename: 'test-file.txt',
				hash: 'test-hash',
				id: 'test-file-id',
				meta: {
					collection_name: 'test-collection',
					content_type: 'text/plain',
					name: 'test-file.txt',
					size: 16,
				},
				updated_at: 1643723900,
				user_id: 'test-user-id',
			});

			mocks.knowledge.addFileToKnowledgeById.mockRejectedValueOnce(new Error('Mock error'));
			const file = new File(['test file content'], 'test-file.txt');
			await expect(addFile('test-knowledge-id', file)).rejects.toThrow('Exception while adding file to knowledge base: Error: Mock error');
		});

		it('should fail if addFileToKnowledgeById() resolves with empty result', async () => {
			mocks.files.uploadFile.mockResolvedValueOnce({
				created_at: 1643723900,
				data: null,
				filename: 'test-file.txt',
				hash: 'test-hash',
				id: 'test-file-id',
				meta: {
					collection_name: 'test-collection',
					content_type: 'text/plain',
					name: 'test-file.txt',
					size: 16,
				},
				updated_at: 1643723900,
				user_id: 'test-user-id',
			});

			mocks.knowledge.addFileToKnowledgeById.mockResolvedValueOnce(undefined);
			const file = new File(['test file content'], 'test-file.txt');
			await expect(addFile('test-knowledge-id', file)).rejects.toThrow('Error adding file to knowledge base knowledge=test-knowledge-id');
		});

		it('should return the result of addFileToKnowledgeById() if it resolves with a knowledge object', async () => {
			const file = new File(['test file content'], 'test-file.txt');
			const uploadedFile = {
				created_at: 1643723900,
				data: null,
				filename: 'test-file.txt',
				hash: 'test-hash',
				id: 'test-file-id',
				meta: {
					collection_name: 'test-collection',
					content_type: 'text/plain',
					name: 'test-file.txt',
					size: 16,
				},
				updated_at: 1643723900,
				user_id: 'test-user-id',
			};

			const knowledge = {
				id: 'test-id',
				user_id: 'test-user-id',
				name: 'Test Knowledge',
				description: 'Test Description',
				data: null,
				access_control: { read: { group_ids: [] }, write: { group_ids: [] } },
				created_at: 1643723900,
				updated_at: 1643723900,
				files: [uploadedFile],
			};

			mocks.files.uploadFile.mockResolvedValueOnce(uploadedFile);
			mocks.knowledge.addFileToKnowledgeById.mockResolvedValueOnce(knowledge);
			const result = await addFile('test-knowledge-id', file);
			expect(result).toEqual([uploadedFile]);
		});
	});
});
