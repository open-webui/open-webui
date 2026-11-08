import {
	joinTerminalPath,
	terminalRequest,
	TerminalRequestError,
	type TerminalConnection,
	type TerminalFileList
} from './index';
import { computeFileHash } from '$lib/utils/hash';

const historyDirectory = (home: string, userId: string) => {
	if (!home || !userId || userId === '.' || userId === '..')
		throw new Error('Terminal home and a valid user are required');
	return joinTerminalPath(home, `.open-webui/users/${encodeURIComponent(userId)}/folders`);
};

export async function loadRecentFolders(
	connection: TerminalConnection,
	chatId: string | null,
	home: string,
	userId: string
): Promise<string[]> {
	const directory = historyDirectory(home, userId);
	let listing: TerminalFileList;
	try {
		listing = await terminalRequest(
			connection,
			chatId,
			`/files/list?directory=${encodeURIComponent(directory)}`
		);
	} catch (error) {
		if (error instanceof TerminalRequestError && error.status === 404) return [];
		throw error;
	}
	const entries = listing.entries
		.filter((entry) => entry.type === 'file' && /^[a-f0-9]{64}\.json$/.test(entry.name))
		.sort((a, b) => (b.modified ?? 0) - (a.modified ?? 0))
		.slice(0, 8);
	const paths = await Promise.all(
		entries.map(async (entry) => {
			try {
				const result = await terminalRequest<{ content: string }>(
					connection,
					chatId,
					`/files/read?path=${encodeURIComponent(joinTerminalPath(directory, entry.name))}`
				);
				const record = JSON.parse(result.content);
				return typeof record?.path === 'string' && record.path ? record.path : null;
			} catch (error) {
				// A missing or partially written record must not hide the rest of the history.
				if (
					error instanceof SyntaxError ||
					(error instanceof TerminalRequestError && error.status === 404)
				)
					return null;
				throw error;
			}
		})
	);
	return [...new Set(paths.filter((path): path is string => path !== null))];
}

export async function rememberRecentFolder(
	connection: TerminalConnection,
	chatId: string | null,
	home: string,
	userId: string,
	path: string
): Promise<void> {
	if (!path) return;
	const normalized = path.replace(/\/+$/, '') || '/';
	const hash = await computeFileHash(new File([normalized], 'folder'));
	// Separate records preserve simultaneous selections in different browsers.
	await terminalRequest(connection, chatId, '/files/write', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			path: joinTerminalPath(historyDirectory(home, userId), `${hash}.json`),
			content: JSON.stringify({ path: normalized })
		})
	});
}
