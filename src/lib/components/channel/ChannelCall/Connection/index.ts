import { SFURTCConnection } from './sfu-rtc';
import type { BaseConnection } from './base';

export type { ConnectionConfig } from './base';

export const ConnectionType = {
	SFU: 'sfu'
} as const;

export type ConnectionTypeValue = (typeof ConnectionType)[keyof typeof ConnectionType];

export function createConnection(type: ConnectionTypeValue): BaseConnection {
	switch (type) {
		case ConnectionType.SFU:
			return new SFURTCConnection();
		default:
			throw new Error(`Unsupported connection type: ${type}`);
	}
}
