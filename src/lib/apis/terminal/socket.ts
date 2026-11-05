import type { TerminalConnection } from './index';

export function assignTerminalChat(socket: WebSocket, chatId: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const finish = (error?: Error) => {
			clearTimeout(timeout);
			socket.removeEventListener('message', onMessage);
			socket.removeEventListener('close', onClose);
			if (error) reject(error);
			else resolve();
		};
		const onMessage = (event: MessageEvent) => {
			if (typeof event.data !== 'string') return;
			try {
				const data = JSON.parse(event.data);
				if (data.type !== 'chat') return;
				if (data.error) finish(new Error(String(data.error)));
				else if (data.chat_id === chatId) finish();
			} catch {
				// Terminal output is not a control message.
			}
		};
		const onClose = () => finish(new Error('Terminal disconnected before joining the chat'));
		const timeout = setTimeout(
			() => finish(new Error('Terminal did not confirm the chat update')),
			10000
		);
		socket.addEventListener('message', onMessage);
		socket.addEventListener('close', onClose);
		try {
			socket.send(JSON.stringify({ type: 'chat', chat_id: chatId }));
		} catch (error) {
			finish(error instanceof Error ? error : new Error(String(error)));
		}
	});
}

export function openTerminalSocket(
	connection: TerminalConnection,
	chatId: string | null,
	path: string,
	onOpen?: (socket: WebSocket) => void,
	resume?: { resume: true; cursor: number; flow_control?: true }
) {
	const url = new URL(`${connection.baseUrl.replace(/\/$/, '')}${path}`, location.href);
	url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
	const socket = new WebSocket(url);
	socket.binaryType = 'arraybuffer';
	socket.onopen = () => {
		socket.send(
			JSON.stringify({
				...resume,
				type: 'auth',
				token: connection.key.trim(),
				chat_id: chatId ?? ''
			})
		);
		onOpen?.(socket);
	};
	return socket;
}

// Streams use the same response bodies as their HTTP endpoints.
export function readTerminalStream<T>(
	connection: TerminalConnection,
	chatId: string | null,
	path: () => string,
	onData: (data: T) => void | Promise<void>,
	onError: (message: string) => void,
	onUnavailable?: () => void
) {
	let stopped = false;
	let received = false;
	let socket: WebSocket | undefined;
	let retry: ReturnType<typeof setTimeout>;
	let delay = 1000;
	let pending = Promise.resolve();
	const connect = async () => {
		// Apply all received output before constructing the reconnect cursor.
		await pending;
		if (stopped) return;
		socket = openTerminalSocket(connection, chatId, path());
		socket.onmessage = (event) => {
			pending = pending
				.then(async () => {
					if (stopped) return;
					const data = JSON.parse(event.data);
					received = true;
					await onData(data);
					delay = 1000;
					onError('');
				})
				.catch(() => onError('Live updates unavailable'));
		};
		socket.onclose = async (event) => {
			await pending;
			if (stopped) return;
			if (!received && onUnavailable && event.code !== 4001 && event.code !== 4003) {
				stopped = true;
				onUnavailable();
				return;
			}
			if (event.code !== 1000) onError('Live updates unavailable');
			if (event.code === 1000 || (event.code >= 4000 && event.code < 5000)) return;
			retry = setTimeout(connect, delay);
			delay = Math.min(delay * 2, 30000);
		};
	};
	void connect();
	return () => {
		stopped = true;
		clearTimeout(retry);
		if (socket) {
			socket.onopen = socket.onmessage = socket.onclose = null;
			socket.close();
		}
	};
}
