import type { TerminalConnection } from './index';

export function watchTerminalFiles(
	connection: TerminalConnection,
	chatId: string | null,
	directory: string,
	onChange: () => void,
	onError: (message: string) => void
) {
	let stopped = false;
	let socket: WebSocket;
	let retry: ReturnType<typeof setTimeout>;
	let retryDelay = 1000;
	const connect = () => {
		const url = new URL(`${connection.baseUrl.replace(/\/$/, '')}/files/events`, location.href);
		url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
		socket = new WebSocket(url);
		socket.onopen = () => {
			socket.send(
				JSON.stringify({ type: 'auth', token: connection.key.trim(), chat_id: chatId ?? '' })
			);
			socket.send(JSON.stringify({ type: 'subscribe', path: directory }));
		};
		socket.onmessage = (event) => {
			if (stopped) return;
			try {
				const message = JSON.parse(event.data);
				if (message.type === 'ready') {
					retryDelay = 1000;
					onError('');
					onChange();
				} else if (message.type === 'change') onChange();
			} catch {
				/* Ignore frames that are not filesystem notifications. */
			}
		};
		socket.onclose = (event) => {
			if (stopped) return;
			onError('Live updates unavailable');
			if (event.code >= 4000 && event.code < 5000) return;
			retry = setTimeout(connect, retryDelay);
			retryDelay = Math.min(retryDelay * 2, 30000);
		};
	};
	connect();
	return () => {
		stopped = true;
		clearTimeout(retry);
		socket.onopen = socket.onmessage = socket.onclose = null;
		socket.close();
	};
}
