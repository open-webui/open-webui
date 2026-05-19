// SFU (Selective Forwarding Unit) connection: each peer sends media to the server,
// which relays tracks to all other peers — avoids direct peer-to-peer mesh.
import type { Socket } from 'socket.io-client';
import {
	BaseConnection,
	type ConnectionConfig,
	type UserInfo,
	type UserMediaStream,
	type OwnedTrack,
	type RemoteTrack
} from './base';

export class SFURTCConnection extends BaseConnection {
	private socket: Socket | null = null;
	private channelId = '';
	private pc: RTCPeerConnection | null = null;
	private offerInFlight = false;
	private negotiationNeeded = false;
	// FIFO queue: one entry per recvonly transceiver added during renegotiation,
	// shifted in ontrack to correlate each incoming track to its source peer
	private pendingRemoteTrackEntries: Array<{
		peer_id: string;
		user: UserInfo | null;
		track_id: string;
	}> = [];
	private peerIdToUser: Record<string, UserInfo> = {};
	private peerIdToVideoStreams: Record<string, MediaStream[]> = {};
	private peerIdToAudioTracks: Record<string, MediaStreamTrack[]> = {};
	private ownedTracks: OwnedTrack[] = [];
	private trackToSender = new Map<MediaStreamTrack, RTCRtpSender>();
	private remoteTracks: RemoteTrack[] = [];
	private screenShareTrack: MediaStreamTrack | null = null;
	private screenShareSender: RTCRtpSender | null = null;
	private screenSharePending = false;

	init(options: ConnectionConfig): void {
		const { channelId, localStream, socket, iceServers = [] } = options;
		if (!socket) throw new Error('SFURTCConnection requires a socket');

		if (this.pc) {
			this.pc.close();
			this.pc = null;
		}

		this.socket = socket;
		this.channelId = channelId;

		this.remoteVideoStreams.set([]);
		this.remoteAudioStream.set(new MediaStream());
		this.connected.set(false);
		this.offerInFlight = false;
		this.negotiationNeeded = false;
		this.pendingRemoteTrackEntries = [];
		this.peerIdToUser = {};
		this.peerIdToVideoStreams = {};
		this.peerIdToAudioTracks = {};
		this.ownedTracks = [];
		this.trackToSender.clear();
		this.remoteTracks = [];
		this.screenShareTrack = null;
		this.screenShareSender = null;
		this.screenSharePending = false;

		this.socket.on('channel:call:answer', this.handleAnswer);
		this.socket.on('channel:call:renegotiate', this.handleRenegotiate);
		this.socket.on('channel:call:peer-left', this.handlePeerLeft);
		this.socket.on('channel:call:track-event', this.handleTrackEvent);

		this.pc = new RTCPeerConnection(iceServers.length > 0 ? { iceServers } : undefined);

		this.pc.onicecandidate = (event) => {
			this.socket?.emit('channel:call:ice-candidate', {
				channel_id: this.channelId,
				data: event.candidate
					? {
							candidate: event.candidate.candidate,
							sdpMid: event.candidate.sdpMid,
							sdpMLineIndex: event.candidate.sdpMLineIndex
						}
					: null
			});
		};

		this.pc.ontrack = this.onTrack;

		this.pc.onconnectionstatechange = () => {
			const connectionState = this.pc?.connectionState;
			console.log(`[call] connection state: ${connectionState}`);
			if (connectionState === 'failed') {
				this.error.set('Call connection failed');
			} else if (connectionState === 'disconnected') {
				this.error.set('Call connection lost');
			}
		};

		this.pc.onnegotiationneeded = () => {
			this.negotiationNeeded = true;
			this.maybeNegotiate();
		};

		for (const track of localStream.getTracks()) {
			const sender = this.pc.addTrack(track, localStream);
			this.trackToSender.set(track, sender);
			this.ownedTracks.push({
				track,
				trackId: null,
				kind: track.kind as 'audio' | 'video',
				isScreenShare: false
			});
		}
	}

	leave(): void {
		console.log('[call] leaving');

		this.socket?.emit('channel:call:leave', { channel_id: this.channelId });
		this.pc?.close();
		this.pc = null;
		this.remoteVideoStreams.set([]);
		this.connected.set(false);
	}

	destroy(): void {
		this.socket?.off('channel:call:answer', this.handleAnswer);
		this.socket?.off('channel:call:renegotiate', this.handleRenegotiate);
		this.socket?.off('channel:call:peer-left', this.handlePeerLeft);
		this.socket?.off('channel:call:track-event', this.handleTrackEvent);
		this.leave();
	}

	setTrackEnabled(kind: 'audio' | 'video', enabled: boolean): void {
		for (const ownedTrack of this.ownedTracks) {
			if (ownedTrack.isScreenShare) continue;
			if (ownedTrack.kind !== kind) continue;

			const sender = this.trackToSender.get(ownedTrack.track);
			sender?.replaceTrack(enabled ? ownedTrack.track : null).catch(() => {});

			if (ownedTrack.trackId) {
				this.emitTrackEvent(ownedTrack.trackId, enabled ? 'on' : 'off');
			}
		}
	}

	async startScreenShare(onScreenShareEnded?: () => void): Promise<void> {
		if (!this.pc || this.screenSharePending) {
			throw new Error('Screen share already pending');
		}
		this.screenSharePending = true;

		try {
			const screenMediaStream = await navigator.mediaDevices.getDisplayMedia({
				video: true,
				audio: false
			});

			// stopScreenShare or leave may have been called while awaiting the picker
			if (!this.pc) {
				screenMediaStream.getTracks().forEach((t) => t.stop());
				return;
			}

			const screenVideoTrack = screenMediaStream.getVideoTracks()[0];
			this.localScreenStream.set(new MediaStream([screenVideoTrack]));
			// addTransceiver (not addTrack) to guarantee a fresh transceiver — addTrack may
			// reuse a recvonly transceiver the server claimed for relay
			const transceiver = this.pc.addTransceiver(screenVideoTrack, { direction: 'sendonly' });
			this.screenShareSender = transceiver.sender;
			this.screenShareTrack = screenVideoTrack;
			this.trackToSender.set(screenVideoTrack, transceiver.sender);

			// trackId assigned when the server's answer arrives
			this.ownedTracks.push({
				track: screenVideoTrack,
				trackId: null,
				kind: 'video',
				isScreenShare: true
			});

			screenVideoTrack.onended = () => {
				this.stopScreenShare();
				onScreenShareEnded?.();
			};
		} catch (err: any) {
			if (err.name !== 'NotAllowedError') {
				this.error.set(`Screen share failed: ${err.message}`);
			}
			// re-throw so the caller (Connection.svelte) can reset its screenSharing flag
			throw err;
		} finally {
			this.screenSharePending = false;
		}
	}

	stopScreenShare(): void {
		if (!this.screenShareTrack) return;

		const screenShareOwnedTrack = this.ownedTracks.find(
			(ownedTrack) => ownedTrack.track === this.screenShareTrack
		);
		if (screenShareOwnedTrack?.trackId) {
			this.emitTrackEvent(screenShareOwnedTrack.trackId, 'kill');
		}

		this.ownedTracks = this.ownedTracks.filter(
			(ownedTrack) => ownedTrack.track !== this.screenShareTrack
		);

		// transceiver stays in the PC with a stopped track — aiortc can't remove transceivers.
		// the stopped track prevents addTrack from reusing it, so the next screen share
		// creates a fresh transceiver and triggers proper renegotiation.
		this.trackToSender.delete(this.screenShareTrack);
		this.screenShareTrack.stop();
		this.screenShareTrack = null;
		this.screenShareSender = null;
		this.localScreenStream.set(null);
	}

	private async maybeNegotiate() {
		if (this.offerInFlight) return;
		if (!this.negotiationNeeded) return;
		if (!this.pc || this.pc.signalingState !== 'stable') return;

		this.negotiationNeeded = false;
		this.offerInFlight = true;

		try {
			const offer = await this.pc.createOffer();
			await this.pc.setLocalDescription(offer);
			this.socket?.emit('channel:call:offer', {
				channel_id: this.channelId,
				data: { sdp: offer.sdp, type: offer.type }
			});
		} catch (err: any) {
			console.error('[call] negotiation error:', err);
			this.offerInFlight = false;
			this.error.set('Call negotiation failed');
		}
	}

	private onTrack = (event: RTCTrackEvent) => {
		const remoteTrackEntry = this.pendingRemoteTrackEntries.shift();
		const peerId = remoteTrackEntry?.peer_id;
		const trackId = remoteTrackEntry?.track_id ?? null;
		const user = remoteTrackEntry?.user || (peerId ? this.peerIdToUser[peerId] : null) || null;

		if (peerId && trackId) {
			this.remoteTracks.push({
				track: event.track,
				trackId,
				peerId,
				kind: event.track.kind as 'audio' | 'video'
			});
		}

		if (event.track.kind === 'video') {
			const videoStream = new MediaStream([event.track]);
			this.remoteVideoStreams.update((streams) => [
				...streams,
				{ stream: videoStream, user, trackId, state: 'on' }
			]);
			if (peerId) {
				this.peerIdToVideoStreams[peerId] = [
					...(this.peerIdToVideoStreams[peerId] || []),
					videoStream
				];
			}
		} else if (event.track.kind === 'audio') {
			this.remoteAudioStream.update((audioStream) => {
				audioStream.addTrack(event.track);
				return audioStream;
			});
			if (peerId) {
				this.peerIdToAudioTracks[peerId] = [
					...(this.peerIdToAudioTracks[peerId] || []),
					event.track
				];
			}
		}
	};

	private handleAnswer = async (event: any) => {
		if (event.channel_id !== this.channelId) return;

		if (this.pc?.signalingState !== 'have-local-offer') {
			console.warn('[call] ignoring answer — not in have-local-offer state');
			return;
		}

		try {
			await this.pc.setRemoteDescription(new RTCSessionDescription(event.data));
			this.connected.set(true);

			// correlate server-assigned track IDs to our unassigned owned tracks
			const newTrackEntries = event.data.track_ids || [];
			const unassignedOwnedTracks = this.ownedTracks.filter(
				(ownedTrack) => ownedTrack.trackId === null
			);
			for (let i = 0; i < newTrackEntries.length && i < unassignedOwnedTracks.length; i++) {
				unassignedOwnedTracks[i].trackId = newTrackEntries[i].track_id;
			}
		} catch (err: any) {
			console.error('[call] failed to set remote description:', err);
			this.error.set('Failed to establish call connection');
		}

		this.offerInFlight = false;
		this.maybeNegotiate();
	};

	private handleRenegotiate = (event: any) => {
		if (event.channel_id !== this.channelId || !this.pc) return;

		// addTransceiver is safe in any signaling state and fires onnegotiationneeded
		const requestedTracks = event.data || [];
		for (const { peer_id, kind, user, track_id } of requestedTracks) {
			this.pc.addTransceiver(kind as string, { direction: 'recvonly' });
			this.pendingRemoteTrackEntries.push({ peer_id, user: user || null, track_id });
			if (user) {
				this.peerIdToUser[peer_id] = user;
			}
		}
	};

	private handlePeerLeft = async (event: any) => {
		if (event.channel_id !== this.channelId) return;

		const peerId = event.data?.peer_id;
		if (!peerId) return;

		console.log(`[call] peer ${peerId} left, cleaning up`);

		const peerVideoStreams = this.peerIdToVideoStreams[peerId] || [];
		if (peerVideoStreams.length > 0) {
			this.remoteVideoStreams.update((streams) =>
				streams.filter((entry) => !peerVideoStreams.includes(entry.stream))
			);
			delete this.peerIdToVideoStreams[peerId];
		}

		const peerAudioTracks = this.peerIdToAudioTracks[peerId] || [];
		if (peerAudioTracks.length > 0) {
			this.remoteAudioStream.update((audioStream) => {
				for (const audioTrack of peerAudioTracks) audioStream.removeTrack(audioTrack);
				return audioStream;
			});
			delete this.peerIdToAudioTracks[peerId];
		}

		delete this.peerIdToUser[peerId];

		this.remoteTracks = this.remoteTracks.filter((remoteTrack) => remoteTrack.peerId !== peerId);
	};

	private emitTrackEvent(trackId: string, action: 'on' | 'off' | 'kill') {
		this.socket?.emit('channel:call:track-event', {
			channel_id: this.channelId,
			data: { track_id: trackId, action }
		});
	}

	private handleTrackEvent = (event: any) => {
		if (event.channel_id !== this.channelId) return;

		const { track_id: trackId, action } = event.data;

		if (action === 'kill') {
			this.remoteVideoStreams.update((streams) =>
				streams.filter((entry) => entry.trackId !== trackId)
			);

			const killedVideoTrack = this.remoteTracks.find(
				(remoteTrack) => remoteTrack.trackId === trackId && remoteTrack.kind === 'video'
			);
			if (killedVideoTrack) {
				for (const [peerId, streams] of Object.entries(this.peerIdToVideoStreams)) {
					this.peerIdToVideoStreams[peerId] = streams.filter(
						(stream) => !stream.getVideoTracks().includes(killedVideoTrack.track)
					);
				}
			}

			const killedAudioTrack = this.remoteTracks.find(
				(remoteTrack) => remoteTrack.trackId === trackId && remoteTrack.kind === 'audio'
			);
			if (killedAudioTrack) {
				this.remoteAudioStream.update((audioStream) => {
					audioStream.removeTrack(killedAudioTrack.track);
					return audioStream;
				});
				for (const peerId of Object.keys(this.peerIdToAudioTracks)) {
					this.peerIdToAudioTracks[peerId] = this.peerIdToAudioTracks[peerId].filter(
						(audioTrack) => audioTrack !== killedAudioTrack.track
					);
				}
			}

			this.remoteTracks = this.remoteTracks.filter(
				(remoteTrack) => remoteTrack.trackId !== trackId
			);
			return;
		}

		this.remoteVideoStreams.update((streams) =>
			streams.map((entry) =>
				entry.trackId === trackId ? { ...entry, state: action as 'on' | 'off' } : entry
			)
		);

		const remoteAudioTrack = this.remoteTracks.find(
			(remoteTrack) => remoteTrack.trackId === trackId && remoteTrack.kind === 'audio'
		);
		if (remoteAudioTrack) {
			remoteAudioTrack.track.enabled = action === 'on';
		}
	};
}
