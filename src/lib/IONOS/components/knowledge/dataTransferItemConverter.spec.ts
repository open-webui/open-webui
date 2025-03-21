import { describe, expect, it, vi } from 'vitest';
import { getFiles } from './dataTransferItemConverter';

describe('dataTransferItemConverter', () => {
  describe('getFiles()', () => {
		it('should ignore entries lacking webkitGetAsEntry()', async () => {
			const mockFiles: FileList = [
				new File(['file content'], 'file.txt', { type: 'text/plain' })
			] as unknown as FileList;
			const mockDataTransferItem = {
				// webkitGetAsEntry() is undefined,
			};
			const mockDataTransfer: DataTransfer = {
				items: [
					mockDataTransferItem as unknown as DataTransferItem,
				] as unknown as DataTransferItemList,
				files: mockFiles,
			} as unknown as DataTransfer;

			const result = await getFiles(mockDataTransfer);

			expect(result.length).toBe(1);
			expect(result[0].name).toBe('file.txt');
		});

		it('should return File objects obtained from file()', async () => {
			const mockFileEntry = {
				isFile: true,
				isDirectory: false,
				filesystem: null,
				fullPath: '/full/path/to/file.txt',
				name: 'file.txt',
				getParent: () => null,
				file: vi.fn().mockImplementation((success) => {
					success(new File(['file content'], 'file.txt', { type: 'text/plain' }));
				}),
			};

			const mockFiles: FileList = [] as unknown as FileList;
			const mockDataTransferItem = {
				webkitGetAsEntry: () => mockFileEntry as unknown as FileSystemEntry,
			};
			const mockDataTransfer: DataTransfer = {
				items: [
					mockDataTransferItem as unknown as DataTransferItem,
				] as unknown as DataTransferItemList,
				files: mockFiles,
			} as unknown as DataTransfer;

			const result = await getFiles(mockDataTransfer);

			expect(result.length).toBe(1);
			expect(result[0].name).toBe('file.txt');
		});
  });
});
