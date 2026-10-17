import { describe, expect, it } from 'vitest';
import { captureDroppedRoots, collectDroppedEntryFiles } from './droppedFiles';

const makeFile = (name: string) => new File([`content of ${name}`], name, { type: 'text/plain' });

const makeFileEntry = (name: string) => ({
        isFile: true,
        isDirectory: false,
        name,
        file: (resolve: (file: File) => void) => resolve(makeFile(name))
});

const makeDirectoryEntry = (name: string, children: any[]) => ({
        isFile: false,
        isDirectory: true,
        name,
        createReader: () => {
                let consumed = false;
                return {
                        readEntries: (resolve: (entries: any[]) => void) => {
                                if (consumed) return resolve([]);
                                consumed = true;
                                resolve(children);
                        }
                };
        }
});

describe('captureDroppedRoots', () => {
        it('captures every dropped folder and file synchronously (#32652)', () => {
                const alpha = makeDirectoryEntry('alpha', [makeFileEntry('a.txt')]);
                const beta = makeDirectoryEntry('beta', [makeFileEntry('b.txt')]);
                const loose = makeFile('loose.txt');

                const dataTransfer = {
                        items: [
                                { webkitGetAsEntry: () => alpha, getAsFile: () => null },
                                { webkitGetAsEntry: () => beta, getAsFile: () => null },
                                { webkitGetAsEntry: () => null, getAsFile: () => loose }
                        ]
                } as unknown as DataTransfer;

                const { entries, files } = captureDroppedRoots(dataTransfer);

                expect(entries.map((entry: any) => entry.name)).toEqual(['alpha', 'beta']);
                expect(files.map((file) => file.name)).toEqual(['loose.txt']);
        });

        it('falls back to dataTransfer.files when there are no items', () => {
                const loose = makeFile('loose.txt');
                const dataTransfer = {
                        items: [],
                        files: [loose]
                } as unknown as DataTransfer;

                const { entries, files } = captureDroppedRoots(dataTransfer);

                expect(entries).toEqual([]);
                expect(files).toEqual([loose]);
        });

        it('returns nothing for an empty drop', () => {
                const { entries, files } = captureDroppedRoots(null);
                expect(entries).toEqual([]);
                expect(files).toEqual([]);
        });
});

describe('collectDroppedEntryFiles', () => {
        it('collects the files of every folder, including nested ones', async () => {
                const alpha = makeDirectoryEntry('alpha', [
                        makeFileEntry('a.txt'),
                        makeDirectoryEntry('nested', [makeFileEntry('n.txt')])
                ]);
                const beta = makeDirectoryEntry('beta', [makeFileEntry('b.txt')]);

                const collected = [
                        ...(await collectDroppedEntryFiles(alpha)),
                        ...(await collectDroppedEntryFiles(beta))
                ];

                expect(collected).toHaveLength(3);
                expect(collected.map((entry) => `${entry.path}/${entry.filename}`).sort()).toEqual([
                        'alpha/a.txt',
                        'alpha/nested/n.txt',
                        'beta/b.txt'
                ]);
                for (const entry of collected) {
                        expect(entry.file.name).toBe(entry.filename);
                }
        });

        it('skips hidden files and folders', async () => {
                const dir = makeDirectoryEntry('dir', [
                        makeFileEntry('.hidden'),
                        makeDirectoryEntry('.git', [makeFileEntry('config')]),
                        makeFileEntry('visible.txt')
                ]);

                const collected = await collectDroppedEntryFiles(dir);

                expect(collected.map((entry) => entry.filename)).toEqual(['visible.txt']);
        });

        it('skips a dropped hidden folder entirely', async () => {
                const hidden = makeDirectoryEntry('.cache', [makeFileEntry('blob.bin')]);

                expect(await collectDroppedEntryFiles(hidden)).toEqual([]);
        });

        it('wraps file read failures with the entry path', async () => {
                const entry = {
                        isFile: true,
                        isDirectory: false,
                        name: 'broken.txt',
                        file: (_resolve: (file: File) => void, reject: (error: Error) => void) =>
                                reject(new Error('NotReadableError'))
                };

                await expect(collectDroppedEntryFiles(entry)).rejects.toThrow('broken.txt');
        });
});
