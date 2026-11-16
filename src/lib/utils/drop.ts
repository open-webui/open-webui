/** A dropped file, or a folder (no `file`), with its path relative to the drop. */
export type DroppedEntry = { path: string; file?: File };

/** Reads a drop's files and folders, walking folders so each file keeps its relative path. */
export async function readDroppedFiles(data: DataTransfer): Promise<DroppedEntry[]> {
	// Capture all roots before the browser locks the drag data after this event.
	const items = Array.from(data.items ?? []).filter((item) => item.kind === 'file');
	const roots = items.map((item) => item.webkitGetAsEntry?.() ?? item.getAsFile());
	if (!items.length) roots.push(...Array.from(data.files));
	const entries: DroppedEntry[] = [];
	async function visit(entry: FileSystemEntry | File, parent = ''): Promise<void> {
		const path = parent + entry.name;
		if (!('isDirectory' in entry)) {
			entries.push({ path, file: entry });
		} else if (entry.isDirectory) {
			entries.push({ path });
			const reader = (entry as FileSystemDirectoryEntry).createReader();
			while (true) {
				const children = await new Promise<FileSystemEntry[]>((resolve, reject) =>
					reader.readEntries(resolve, reject)
				);
				if (!children.length) break;
				for (const child of children) await visit(child, `${path}/`);
			}
		} else {
			const file = await new Promise<File>((resolve, reject) =>
				(entry as FileSystemFileEntry).file(resolve, reject)
			);
			entries.push({ path, file });
		}
	}
	for (const root of roots) {
		if (!root) throw new Error('Unable to read a dropped file or folder.');
		await visit(root);
	}
	return entries;
}
