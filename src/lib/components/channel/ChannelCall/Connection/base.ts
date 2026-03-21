import { writable, type Writable } from 'svelte/store';

export type UserInfo = {
	id: string;
	name: string;
	role: string;
};

export type UserMediaStream = {
	stream: MediaStream;
	user: UserInfo | null;
	trackId: string | null;
	state: 'on' | 'off' | 'killed';
};

export type OwnedTrack = {
	track: MediaStreamTrack;
	trackId: string | null;
	kind: 'audio' | 'video';
	isScreenShare: boolean;
};

export type RemoteTrack = {
	track: MediaStreamTrack;
	trackId: string;
	peerId: string;
	kind: 'audio' | 'video';
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
	readonly localScreenStream: Writable<MediaStream | null> = writable(null);

	abstract init(options: ConnectionConfig): void;
	abstract leave(): void;
	abstract destroy(): void;
	abstract setTrackEnabled(kind: 'audio' | 'video', enabled: boolean): void;
	abstract startScreenShare(onScreenShareEnded?: () => void): Promise<void>;
	abstract stopScreenShare(): void;
}

export { BaseConnection, type ConnectionConfig };
