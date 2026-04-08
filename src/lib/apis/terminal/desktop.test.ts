/**
 * Unit tests for the desktop (noVNC) API helpers in src/lib/apis/terminal/index.ts
 *
 * We mock fetch globally so no network calls are made.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/constants', () => ({
	WEBUI_API_BASE_URL: 'http://localhost:8080/api'
}));

import {
	getDesktopStatus,
	startDesktop,
	stopDesktop,
	getDesktopViewerUrl,
	getPortProxyUrl
} from '$lib/apis/terminal';

const BASE = 'http://terminal:8080';
const API_KEY = 'test-key';

beforeEach(() => {
	vi.restoreAllMocks();
});

describe('getDesktopStatus', () => {
	it('returns parsed DesktopStatus on success', async () => {
		const body = {
			running: true,
			display: ':0',
			vnc_port: 5900,
			novnc_port: 6080,
			screen_width: 1280,
			screen_height: 720
		};
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(body)
		});

		const result = await getDesktopStatus(BASE, API_KEY);
		expect(result).toEqual(body);
		expect(fetch).toHaveBeenCalledWith(
			'http://terminal:8080/desktop',
			expect.objectContaining({
				headers: { Authorization: 'Bearer test-key' }
			})
		);
	});

	it('returns null on non-ok response', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({ ok: false });
		const result = await getDesktopStatus(BASE, API_KEY);
		expect(result).toBeNull();
	});

	it('returns null on network error', async () => {
		globalThis.fetch = vi.fn().mockRejectedValue(new Error('network'));
		const result = await getDesktopStatus(BASE, API_KEY);
		expect(result).toBeNull();
	});
});

describe('startDesktop', () => {
	it('posts to desktop/start and returns status', async () => {
		const body = { running: true, novnc_port: 6080 };
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(body)
		});

		const result = await startDesktop(BASE, API_KEY);
		expect(result).toEqual(body);
		expect(fetch).toHaveBeenCalledWith(
			'http://terminal:8080/desktop/start',
			expect.objectContaining({ method: 'POST' })
		);
	});

	it('returns null on failure', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: false,
			json: () => Promise.resolve({ detail: 'error' })
		});
		const result = await startDesktop(BASE, API_KEY);
		expect(result).toBeNull();
	});
});

describe('stopDesktop', () => {
	it('returns true on success', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });
		const result = await stopDesktop(BASE, API_KEY);
		expect(result).toBe(true);
		expect(fetch).toHaveBeenCalledWith(
			'http://terminal:8080/desktop/stop',
			expect.objectContaining({ method: 'POST' })
		);
	});

	it('returns false on failure', async () => {
		globalThis.fetch = vi.fn().mockRejectedValue(new Error('fail'));
		const result = await stopDesktop(BASE, API_KEY);
		expect(result).toBe(false);
	});
});

describe('getDesktopViewerUrl', () => {
	it('builds viewer URL with default port', () => {
		expect(getDesktopViewerUrl('http://host:8080')).toBe('http://host:8080/proxy/6080/vnc.html');
	});

	it('builds viewer URL with custom port', () => {
		expect(getDesktopViewerUrl('http://host:8080', 6090)).toBe(
			'http://host:8080/proxy/6090/vnc.html'
		);
	});

	it('strips trailing slash', () => {
		expect(getDesktopViewerUrl('http://host:8080/')).toBe('http://host:8080/proxy/6080/vnc.html');
	});
});

describe('getPortProxyUrl', () => {
	it('builds proxy URL with path', () => {
		expect(getPortProxyUrl('http://host:8080', 3000, 'api/data')).toBe(
			'http://host:8080/proxy/3000/api/data'
		);
	});

	it('builds proxy URL without path', () => {
		expect(getPortProxyUrl('http://host:8080', 3000)).toBe('http://host:8080/proxy/3000/');
	});
});
