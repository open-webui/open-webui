import { writable, type Writable } from 'svelte/store';

export type UserInfo = {
	id: string;
	name: string;
	role: string;
};

export type UserMediaStream = {
	stream: MediaStream;
	user: UserInfo | null;
};

type ConnectionConfig = {
	channelId: string;
	localStream: MediaStream;

	// WebRTC-based implementations (SFU — Selective Forwarding Unit, mesh)
	socket?: any;
	iceServers?: RTCIceServer[];

	// non-WebRTC implementations (WebTransport, WebSocket)
	serverUrl?: string;
};

abstract class BaseConnection {
	readonly remoteVideoStreams: Writable<UserMediaStream[]> = writable([]);
	readonly remoteAudioStream: Writable<MediaStream> = writable(new MediaStream());
	readonly connected: Writable<boolean> = writable(false);
	readonly error: Writable<string | null> = writable(null);

	abstract init(options: ConnectionConfig): void;
	abstract leave(): void;
	abstract destroy(): void;
}

export { BaseConnection, type ConnectionConfig };
