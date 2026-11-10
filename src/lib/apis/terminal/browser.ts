import { terminalRequest, type TerminalTarget } from './index';

export type BrowserSession = {
	id: string;
	token: string;
	url: string;
	title: string;
	mode: 'proxy' | 'chrome';
	chrome_available: boolean;
};

export const getBrowserSession = (target: TerminalTarget, id: string) =>
	terminalRequest<BrowserSession>(target, `/browser/sessions/${encodeURIComponent(id)}`);

export const createBrowserSession = async (target: TerminalTarget, url = '') => {
	const session = await terminalRequest<BrowserSession>(target, '/browser/sessions', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ url })
	});
	if (!session.chrome_available || session.mode === 'chrome') return session;
	try {
		return await updateBrowserSession(target, session.id, { mode: 'chrome' });
	} catch {
		// Reset the server too: Chrome startup may have failed after changing the mode.
		return updateBrowserSession(target, session.id, { mode: 'proxy' });
	}
};

export const updateBrowserSession = (
	target: TerminalTarget,
	id: string,
	fields: Partial<Pick<BrowserSession, 'url' | 'title' | 'mode'>> & {
		active?: boolean;
		chat_id?: string;
	}
) =>
	terminalRequest<BrowserSession>(target, `/browser/sessions/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(fields)
	});

export const closeBrowserSession = (target: TerminalTarget, id: string) =>
	terminalRequest(target, `/browser/sessions/${encodeURIComponent(id)}`, {
		method: 'DELETE',
		keepalive: true
	});

export const browserViewUrl = (target: TerminalTarget, session: BrowserSession) =>
	`${target.baseUrl.replace(/\/$/, '')}/browser/view/${encodeURIComponent(session.id)}/${encodeURIComponent(session.token)}`;

export function browserFrameUrl(prefix: string, value: string) {
	const url = new URL(value);
	return `${prefix}/frame/${url.protocol.slice(0, -1)}/${encodeURIComponent(url.host)}${url.pathname}${url.search}${url.hash}`;
}
