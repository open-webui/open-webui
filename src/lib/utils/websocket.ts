import { io } from 'socket.io-client';

import { socket, activeUserIds, USAGE_POOL } from '$lib/stores';
import { WEBUI_BASE_URL } from '$lib/constants';

export const setupSocket = async (enableWebsocket) => {
	const _socket = io(`${WEBUI_BASE_URL}` || undefined, {
		reconnection: true,
		reconnectionDelay: 1000,
		reconnectionDelayMax: 5000,
		randomizationFactor: 0.5,
		path: '/ws/socket.io',
		transports: enableWebsocket ? ['websocket'] : ['polling', 'websocket'],
		auth: { token: localStorage.token }
	});

	await socket.set(_socket);

	_socket.on('connect_error', (err) => {
		console.log('connect_error', err);
	});

	_socket.on('connect', () => {
		console.log('connected', _socket.id);
	});

	_socket.on('reconnect_attempt', (attempt) => {
		console.log('reconnect_attempt', attempt);
	});

	_socket.on('reconnect_failed', () => {
		console.log('reconnect_failed');
	});

	_socket.on('disconnect', (reason, details) => {
		console.log(`Socket ${_socket.id} disconnected due to ${reason}`);
		if (details) {
			console.log('Additional details:', details);
		}
	});

	_socket.on('user-list', (data) => {
		console.log('user-list', data);
		activeUserIds.set(data.user_ids);
	});

	_socket.on('usage', (data) => {
		console.log('usage', data);
		USAGE_POOL.set(data['models']);
	});
};
