import type { ListeningPort, TerminalConnection } from './index';
import { openTerminalSocket } from './socket';

function watchTerminalEvents(
	connection: TerminalConnection,
	chatId: string | null,
	subscription: { path?: string; ports?: boolean },
	onMessage: (message: any) => void,
	onError: (message: string) => void
) {
	let stopped = false;
	let socket: WebSocket;
	let retry: ReturnType<typeof setTimeout>;
	let retryDelay = 1000;
	const connect = () => {
		socket = openTerminalSocket(connection, chatId, '/events', (socket) => {
			socket.send(JSON.stringify({ type: 'subscribe', ...subscription }));
		});
		socket.onmessage = (event) => {
			if (stopped) return;
			try {
				const message = JSON.parse(event.data);
				retryDelay = 1000;
				onError('');
				onMessage(message);
			} catch {
				/* Ignore invalid event frames. */
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

export function watchTerminalFiles(
	connection: TerminalConnection,
	chatId: string | null,
	directory: string,
	onChange: () => void,
	onError: (message: string) => void
) {
	return watchTerminalEvents(
		connection,
		chatId,
		{ path: directory },
		(message) => {
			if (message.type === 'fs:ready' || message.type === 'fs:change') onChange();
		},
		onError
	);
}

export function watchTerminalPorts(
	connection: TerminalConnection,
	chatId: string | null,
	onPorts: (ports: ListeningPort[]) => void,
	onError: (message: string) => void
) {
	return watchTerminalEvents(
		connection,
		chatId,
		{ ports: true },
		(message) => {
			if (message.type === 'ports:change') onPorts(message.ports);
		},
		onError
	);
}
