export type DroppedDirectoryFileEntry = { path: string; filename: string; file: File };

const hasHiddenFolder = (path: string) => path.split('/').some((part) => part.startsWith('.'));

export const readDirectoryEntries = async (
        reader: FileSystemDirectoryReader
): Promise<FileSystemEntry[]> => {
        const entries: FileSystemEntry[] = [];

        while (true) {
                const batch = await new Promise<FileSystemEntry[]>((resolve, reject) => {
                        reader.readEntries(resolve, reject);
                });

                if (batch.length === 0) {
                        break;
                }

                entries.push(...batch);
        }

        return entries;
};

export const collectDroppedEntryFiles = async (
        entry: FileSystemEntry,
        entryPath = entry.name
): Promise<DroppedDirectoryFileEntry[]> => {
        if (entry.name.startsWith('.') || hasHiddenFolder(entryPath)) {
                return [];
        }

        if (entry.isFile) {
                let file: File;
                try {
                        file = await new Promise<File>((resolve, reject) => {
                                (entry as FileSystemFileEntry).file(resolve, reject);
                        });
                } catch (error) {
                        throw new Error(`"${entryPath}": ${error}`);
                }
                const parts = entryPath.split('/');
                const filename = parts.pop() || file.name;
                return [{ path: parts.join('/'), filename, file }];
        }

        if (entry.isDirectory) {
                const reader = (entry as FileSystemDirectoryEntry).createReader();
                const entries = await readDirectoryEntries(reader);
                const nested = await Promise.all(
                        entries.map((child) => collectDroppedEntryFiles(child, `${entryPath}/${child.name}`))
                );
                return nested.flat();
        }

        return [];
};

/**
 * Capture the roots of a drop synchronously. DataTransferItem entries are
 * released by the browser as soon as the drop event handling yields, so every
 * item must be read before the first await — reading them one by one across
 * awaits drops all but the first folder (#32652).
 */
export const captureDroppedRoots = (
        dataTransfer: DataTransfer | null | undefined
): { entries: FileSystemEntry[]; files: File[] } => {
        const items = Array.from(dataTransfer?.items ?? []);
        const entries: FileSystemEntry[] = [];
        const files: File[] = [];

        for (const rawItem of items) {
                const item = rawItem as DataTransferItem & { webkitGetAsEntry?: () => FileSystemEntry | null };
                const entry = item.webkitGetAsEntry?.();

                if (entry?.isDirectory) {
                        entries.push(entry);
                } else {
                        const file = item.getAsFile?.();
                        if (file) files.push(file);
                }
        }

        if (items.length === 0) {
                files.push(...Array.from(dataTransfer?.files ?? []));
        }

        return { entries, files };
};
