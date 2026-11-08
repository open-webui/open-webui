import type { GitFile, GitStatus } from '$lib/apis/terminal/git';

export const gitTreePath = (path: string) =>
	path
		.replace(/\\/g, '/')
		.replace(/\/{2,}/g, '/')
		.replace(/\/$/, '');

const priority: Record<string, number> = {
	conflict: 7,
	deleted: 6,
	renamed: 5,
	added: 4,
	untracked: 4,
	modified: 3,
	'type-changed': 3,
	copied: 2
};

export function gitTreeStatus(status: GitStatus | null): Map<string, GitFile> {
	const entries = new Map<string, GitFile>();
	if (!status?.is_repo || !status.root) return entries;
	const root = gitTreePath(status.root);
	for (const file of status.files) {
		let path = gitTreePath(`${root}/${file.path}`);
		// Decorate ancestors even when the changed file is deleted or its folder is collapsed.
		while (path === root || path.startsWith(`${root}/`)) {
			const previous = entries.get(path);
			if (!previous || (priority[file.status] ?? 1) > (priority[previous.status] ?? 1)) {
				entries.set(path, file);
			}
			if (path === root) break;
			path = path.slice(0, path.lastIndexOf('/'));
		}
	}
	return entries;
}
