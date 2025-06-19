/**
 * Get File object from FileEntry
 * https://wicg.github.io/entries-api/#api-fileentry
 */
function getFileFromEntry(entry: FileSystemFileEntry): Promise<File> {
	return new Promise((resolve, reject) => {
		entry.file(resolve, reject);
	});
}

/**
 * Get files from the dataTransfer.
 * Filter out directories
 */
export const getFiles = async (dataTransfer: DataTransfer): Promise<File[]> => {
	if (!dataTransfer?.items?.[0]?.webkitGetAsEntry) {
		// webkitGetAsEntry() not supported
		return [...dataTransfer.files];
	}

	// @ts-expect-error Type '(FileSystemEntry | null)[]' is not assignable to type 'FileSystemFileEntry[]'.
	const entries: FileSystemFileEntry[] =
		[...dataTransfer.items]
			.map((item) => item.webkitGetAsEntry())
			.filter((entry) => entry?.isFile);

	const files: File[] = [];

	for (const entry of entries) {
		files.push(await getFileFromEntry(entry));
	}

	return files;
}
