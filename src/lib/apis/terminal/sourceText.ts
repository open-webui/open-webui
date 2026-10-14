export const MAX_COMPARISON_BYTES = 2 * 1024 * 1024;

export const checkSourceSize = (size?: number) => {
	if (size !== undefined && size > MAX_COMPARISON_BYTES)
		throw new Error('File exceeds the 2 MiB comparison limit.');
};

/** Read complete UTF-8 source, never a truncated preview or binary placeholder. */
export async function readSourceResponse(response: Response, signal: AbortSignal): Promise<string> {
	signal.throwIfAborted();
	if (!response.ok) {
		const message =
			response.status === 404
				? 'File not found.'
				: response.status === 401 || response.status === 403
					? 'Permission denied.'
					: 'Could not read file.';
		await response.body?.cancel();
		throw new Error(message);
	}
	const contentType = response.headers.get('content-type') ?? '';
	// application/octet-stream is also used for extensionless text; inspect its bytes.
	if (
		/^(image\/(?!svg\+xml)|audio\/|video\/)|application\/(pdf|zip|x-gzip|gzip|vnd\.|msword)/i.test(
			contentType
		)
	) {
		await response.body?.cancel();
		throw new Error('This file is not supported for source comparison.');
	}
	const reader = response.body?.getReader();
	if (!reader) throw new Error('Could not read file.');
	const cancel = () => void reader.cancel().catch(() => {});
	signal.addEventListener('abort', cancel, { once: true });
	try {
		checkSourceSize(Number(response.headers.get('content-length') ?? 0));
		const decoder = new TextDecoder('utf-8', { fatal: true });
		let size = 0;
		let text = '';
		while (true) {
			signal.throwIfAborted();
			const { done, value } = await reader.read();
			signal.throwIfAborted();
			if (done) break;
			size += value.byteLength;
			checkSourceSize(size);
			try {
				text += decoder.decode(value, { stream: true });
			} catch {
				throw new Error('Only UTF-8 text files are supported for source comparison.');
			}
		}
		try {
			text += decoder.decode();
		} catch {
			throw new Error('Only UTF-8 text files are supported for source comparison.');
		}
		if (/[\x00-\x08\x0e-\x1f\x7f]/.test(text))
			throw new Error('This file is not supported for source comparison.');
		return text;
	} finally {
		signal.removeEventListener('abort', cancel);
		await reader.cancel().catch(() => {});
		reader.releaseLock();
	}
}
