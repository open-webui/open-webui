import { describe, expect, it, vi } from 'vitest';

import { withDownloadLock } from './downloadState';

describe('withDownloadLock', () => {
	it('prevents duplicate concurrent downloads for the same path', async () => {
		const inFlight = new Set<string>();
		let resolveDownload: (value: string) => void = () => {};
		const download = vi.fn(
			() =>
				new Promise<string>((resolve) => {
					resolveDownload = resolve;
				})
		);

		const first = withDownloadLock(inFlight, '/large-folder/', () => {}, download);
		const duplicate = await withDownloadLock(inFlight, '/large-folder/', () => {}, download);

		expect(duplicate).toBeUndefined();
		expect(download).toHaveBeenCalledTimes(1);
		expect(inFlight.has('/large-folder/')).toBe(true);

		resolveDownload('archive');
		await expect(first).resolves.toBe('archive');
		expect(inFlight.has('/large-folder/')).toBe(false);
	});

	it('releases the path after a failed download', async () => {
		const inFlight = new Set<string>();
		const download = vi.fn().mockRejectedValue(new Error('archive failed'));

		await expect(withDownloadLock(inFlight, '/large-folder/', () => {}, download)).rejects.toThrow(
			'archive failed'
		);
		expect(inFlight.has('/large-folder/')).toBe(false);
	});
});
