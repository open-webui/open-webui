// SFU (Selective Forwarding Unit) connection: each peer sends media to the server,
// which relays tracks to all other peers — avoids direct peer-to-peer mesh.
import type { Socket } from 'socket.io-client';
import { BaseConnection, type ConnectionConfig, type UserInfo, type UserMediaStream } from './base';

export class SFURTCConnection extends BaseConnection {
	private socket: Socket | null = null;
	private channelId = '';
	private pc: RTCPeerConnection | null = null;
	// true while the server is driving a renegotiation; suppresses client-initiated negotiation
	private serverRenegotiating = false;
	// queue of peer info, one per transceiver added during renegotiation; shifted in ontrack to correlate tracks to peers
	private pendingTrackPeers: Array<{ peer_id: string; user: UserInfo | null }> = [];
	private peerIdToUser: Record<string, UserInfo> = {};
	private peerIdToVideoStreams: Record<string, MediaStream[]> = {};
	private peerIdToAudioTracks: Record<string, MediaStreamTrack[]> = {};

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
		this.serverRenegotiating = false;
		this.pendingTrackPeers = [];
		this.peerIdToUser = {};
		this.peerIdToVideoStreams = {};
		this.peerIdToAudioTracks = {};

		// socket listeners
		this.socket.on('channel:call:answer', this.handleAnswer);
		this.socket.on('channel:call:renegotiate', this.handleRenegotiate);
		this.socket.on('channel:call:peer-left', this.handlePeerLeft);

		// peer connection
		this.pc = new RTCPeerConnection(iceServers.length > 0 ? { iceServers } : undefined);

		this.pc.onicecandidate = (e) => {
			this.socket?.emit('channel:call:ice-candidate', {
				channel_id: this.channelId,
				data: e.candidate
					? {
							candidate: e.candidate.candidate,
							sdpMid: e.candidate.sdpMid,
							sdpMLineIndex: e.candidate.sdpMLineIndex
						}
					: null
			});
		};

		this.pc.ontrack = this.onTrack;

		this.pc.onconnectionstatechange = () => {
			const state = this.pc?.connectionState;
			console.log(`[call] connection state: ${state}`);
			if (state === 'failed') {
				this.error.set('Call connection failed');
			} else if (state === 'disconnected') {
				this.error.set('Call connection lost');
			}
		};

		this.pc.onnegotiationneeded = async () => {
			try {
				if (this.serverRenegotiating) return;
				if (this.pc?.signalingState !== 'stable') return;
				const offer = await this.pc.createOffer();
				await this.pc.setLocalDescription(offer);
				this.emitOffer(offer);
			} catch (err: any) {
				console.error('[call] negotiation error:', err);
				this.error.set('Call negotiation failed');
			}
		};

		// will trigger negotiationneeded
		for (const track of localStream.getTracks()) {
			this.pc.addTrack(track, localStream);
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
		this.leave();
	}

	private emitOffer = (offer: RTCSessionDescriptionInit) => {
		this.socket?.emit('channel:call:offer', {
			channel_id: this.channelId,
			data: { sdp: offer.sdp, type: offer.type }
		});
	};

	// tracks arrive in the same order as transceivers were added, so shift() correlates each track to its peer
	private onTrack = (e: RTCTrackEvent) => {
		const peerInfo = this.pendingTrackPeers.shift();
		const peerId = peerInfo?.peer_id;
		const user = peerInfo?.user || (peerId ? this.peerIdToUser[peerId] : null) || null;

		if (e.track.kind === 'video') {
			const stream = new MediaStream([e.track]);
			this.remoteVideoStreams.update((s) => [...s, { stream, user }]);
			if (peerId) {
				this.peerIdToVideoStreams[peerId] = [...(this.peerIdToVideoStreams[peerId] || []), stream];
			}
			console.log(`[call] received video stream${peerId ? ` from peer ${peerId}` : ''}`);
		} else if (e.track.kind === 'audio') {
			this.remoteAudioStream.update((s) => {
				s.addTrack(e.track);
				return s;
			});
			if (peerId) {
				this.peerIdToAudioTracks[peerId] = [...(this.peerIdToAudioTracks[peerId] || []), e.track];
			}
			console.log(`[call] received audio stream${peerId ? ` from peer ${peerId}` : ''}`);
		}
	};

	private handleAnswer = async (event: any) => {
		if (event.channel_id !== this.channelId) return;

		console.log('[call] received answer');

		if (this.pc?.signalingState !== 'have-local-offer') {
			console.log('[call] ignoring answer, not in have-local-offer state');
			return;
		}

		try {
			await this.pc.setRemoteDescription(new RTCSessionDescription(event.data));
			this.serverRenegotiating = false;
			this.connected.set(true);
		} catch (err: any) {
			console.error('[call] failed to set remote description:', err);
			this.error.set('Failed to establish call connection');
		}
	};

	private handleRenegotiate = async (event: any) => {
		if (event.channel_id !== this.channelId || !this.pc) return;

		console.log('[call] received renegotiate');

		if (this.pc.signalingState !== 'stable') {
			console.log('[call] deferring renegotiate until stable');
			this.pc.addEventListener('signalingstatechange', () => this.handleRenegotiate(event), {
				once: true
			});
			return;
		}

		try {
			// add recvonly transceivers and queue peer info for ontrack correlation
			this.serverRenegotiating = true;
			const requestedTransceivers = event.data || [];
			for (const { peer_id, kind, user } of requestedTransceivers) {
				this.pc.addTransceiver(kind as string, { direction: 'recvonly' });
				this.pendingTrackPeers.push({ peer_id, user: user || null });
				if (user) {
					this.peerIdToUser[peer_id] = user;
				}
			}
			const offer = await this.pc.createOffer();
			await this.pc.setLocalDescription(offer);
			this.emitOffer(offer);
		} catch (err: any) {
			console.error('[call] renegotiation error:', err);
			this.error.set('Failed to add peer to call');
			this.serverRenegotiating = false;
		}
	};

	private handlePeerLeft = async (event: any) => {
		if (event.channel_id !== this.channelId) return;

		const peerId = event.data?.peer_id;
		if (!peerId) return;

		console.log(`[call] peer ${peerId} left, cleaning up`);

		// remove video streams belonging to this peer
		const peerStreams = this.peerIdToVideoStreams[peerId] || [];
		if (peerStreams.length > 0) {
			this.remoteVideoStreams.update((s) => s.filter((v) => !peerStreams.includes(v.stream)));
			delete this.peerIdToVideoStreams[peerId];
		}

		// remove audio tracks belonging to this peer
		const peerAudioTracks = this.peerIdToAudioTracks[peerId] || [];
		if (peerAudioTracks.length > 0) {
			this.remoteAudioStream.update((s) => {
				for (const track of peerAudioTracks) s.removeTrack(track);
				return s;
			});
			delete this.peerIdToAudioTracks[peerId];
		}

		delete this.peerIdToUser[peerId];
	};
}
