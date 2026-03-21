import json
import uuid
from typing import List, Optional, Tuple
from dataclasses import dataclass

import pycrdt as Y
from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.redis import get_redis_connection

import asyncio
from pyee.asyncio import AsyncIOEventEmitter

import aiortc
from aiortc import MediaStreamTrack
from aiortc.contrib.media import MediaRelay
from aiortc.rtcicetransport import candidate_from_aioice
from aioice.candidate import Candidate as AioIceCandidate

import logging
log = logging.getLogger(__name__)


class RedisLock:
    def __init__(
        self,
        redis_url,
        lock_name,
        timeout_secs,
        redis_sentinels=[],
        redis_cluster=False,
    ):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        self.redis = get_redis_connection(
            redis_url,
            redis_sentinels,
            redis_cluster=redis_cluster,
            decode_responses=True,
        )

    def aquire_lock(self):
        # nx=True will only set this key if it _hasn't_ already been set
        self.lock_obtained = self.redis.set(self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs)
        return self.lock_obtained

    def renew_lock(self):
        # xx=True will only set this key if it _has_ already been set
        return self.redis.set(self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs)

    def release_lock(self):
        lock_value = self.redis.get(self.lock_name)
        if lock_value and lock_value == self.lock_id:
            self.redis.delete(self.lock_name)


class RedisDict:
    def __init__(self, name, redis_url, redis_sentinels=[], redis_cluster=False):
        self.name = name
        self.redis = get_redis_connection(
            redis_url,
            redis_sentinels,
            redis_cluster=redis_cluster,
            decode_responses=True,
        )

    def __setitem__(self, key, value):
        serialized_value = json.dumps(value)
        self.redis.hset(self.name, key, serialized_value)

    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is None:
            raise KeyError(key)
        return json.loads(value)

    def __delitem__(self, key):
        result = self.redis.hdel(self.name, key)
        if result == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __len__(self):
        return self.redis.hlen(self.name)

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        return [json.loads(v) for v in self.redis.hvals(self.name)]

    def items(self):
        return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]

    def set(self, mapping: dict):
        if not mapping:
            self.redis.delete(self.name)
            return

        # Fetch existing keys before writing so we know which ones to remove.
        # HKEYS is cheap — it transfers only short key strings, not large JSON values.
        existing_keys = set(self.redis.hkeys(self.name))
        new_keys = set(mapping.keys())
        keys_to_remove = existing_keys - new_keys

        # HSET first (add/update all new values), then HDEL (remove stale keys).
        # We never DELETE the whole hash — this eliminates the race window
        # where concurrent readers would see an empty models dict.
        self.redis.hset(self.name, mapping={k: json.dumps(v) for k, v in mapping.items()})
        if keys_to_remove:
            self.redis.hdel(self.name, *keys_to_remove)

    def setnx(self, key, value):
        serialized_value = json.dumps(value)

        # set key only if it doesn't exist - returns True if set, False otherwise
        return self.redis.hsetnx(self.name, key, serialized_value)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        self.redis.delete(self.name)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if hasattr(other, 'items') else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class YdocManager:
    COMPACTION_THRESHOLD = 500

    def __init__(
        self,
        redis=None,
        redis_key_prefix: str = f'{REDIS_KEY_PREFIX}:ydoc:documents',
    ):
        self._updates = {}
        self._users = {}
        self._redis = redis
        self._redis_key_prefix = redis_key_prefix

    async def append_to_updates(self, document_id: str, update: bytes):
        document_id = document_id.replace(':', '_')
        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:updates'
            await self._redis.rpush(redis_key, json.dumps(list(update)))
            list_len = await self._redis.llen(redis_key)
            if list_len >= self.COMPACTION_THRESHOLD:
                await self._compact_updates_redis(document_id)
        else:
            if document_id not in self._updates:
                self._updates[document_id] = []
            self._updates[document_id].append(update)
            if len(self._updates[document_id]) >= self.COMPACTION_THRESHOLD:
                self._compact_updates_memory(document_id)

    async def _compact_updates_redis(self, document_id: str):
        """Rolling compaction: squash oldest half into one snapshot."""
        redis_key = f'{self._redis_key_prefix}:{document_id}:updates'
        all_updates = await self._redis.lrange(redis_key, 0, -1)
        if len(all_updates) <= 1:
            return
        mid = len(all_updates) // 2
        ydoc = Y.Doc()
        for raw in all_updates[:mid]:
            ydoc.apply_update(bytes(json.loads(raw)))
        snapshot = json.dumps(list(ydoc.get_update()))
        pipe = self._redis.pipeline()
        pipe.delete(redis_key)
        pipe.rpush(redis_key, snapshot, *all_updates[mid:])
        await pipe.execute()

    def _compact_updates_memory(self, document_id: str):
        """Rolling compaction: squash oldest half into one snapshot."""
        updates = self._updates.get(document_id, [])
        if len(updates) <= 1:
            return
        mid = len(updates) // 2
        ydoc = Y.Doc()
        for update in updates[:mid]:
            ydoc.apply_update(bytes(update))
        self._updates[document_id] = [ydoc.get_update()] + updates[mid:]

    async def get_updates(self, document_id: str) -> List[bytes]:
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:updates'
            updates = await self._redis.lrange(redis_key, 0, -1)
            return [bytes(json.loads(update)) for update in updates]
        else:
            return self._updates.get(document_id, [])

    async def document_exists(self, document_id: str) -> bool:
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:updates'
            return await self._redis.exists(redis_key) > 0
        else:
            return document_id in self._updates

    async def get_users(self, document_id: str) -> List[str]:
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:users'
            users = await self._redis.smembers(redis_key)
            return list(users)
        else:
            return self._users.get(document_id, [])

    async def add_user(self, document_id: str, user_id: str):
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:users'
            await self._redis.sadd(redis_key, user_id)
        else:
            if document_id not in self._users:
                self._users[document_id] = set()
            self._users[document_id].add(user_id)

    async def remove_user(self, document_id: str, user_id: str):
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:users'
            await self._redis.srem(redis_key, user_id)
        else:
            if document_id in self._users and user_id in self._users[document_id]:
                self._users[document_id].remove(user_id)

    async def remove_user_from_all_documents(self, user_id: str):
        if self._redis:
            keys = []
            async for key in self._redis.scan_iter(match=f'{self._redis_key_prefix}:*', count=100):
                keys.append(key)
            for key in keys:
                if key.endswith(':users'):
                    await self._redis.srem(key, user_id)

                    document_id = key.split(':')[-2]
                    if len(await self.get_users(document_id)) == 0:
                        await self.clear_document(document_id)

        else:
            for document_id in list(self._users.keys()):
                if user_id in self._users[document_id]:
                    self._users[document_id].remove(user_id)
                    if not self._users[document_id]:
                        del self._users[document_id]

                        await self.clear_document(document_id)

    async def clear_document(self, document_id: str):
        document_id = document_id.replace(':', '_')

        if self._redis:
            redis_key = f'{self._redis_key_prefix}:{document_id}:updates'
            await self._redis.delete(redis_key)
            redis_users_key = f'{self._redis_key_prefix}:{document_id}:users'
            await self._redis.delete(redis_users_key)
        else:
            if document_id in self._updates:
                del self._updates[document_id]
            if document_id in self._users:
                del self._users[document_id]


@dataclass
class TrackInfo:
    track: MediaStreamTrack
    track_id: str
    kind: str  # 'audio' | 'video'


@dataclass
class TrackMetadata:
    sid: str
    kind: str


@dataclass
class PendingTrack:
    peer_id: str
    track: MediaStreamTrack
    track_id: str


@dataclass
class RenegotiationEntry:
    peer_id: str
    kind: str
    track_id: str


@dataclass
class OfferResult:
    description: aiortc.RTCSessionDescription
    new_tracks: list[TrackInfo]


# SFU (Selective Forwarding Unit) — a server-side WebRTC relay that receives each
# peer's media tracks and selectively forwards them to every other peer in the call,
# avoiding the O(n^2) mesh of direct peer-to-peer connections."""
class SelectiveForwardingUnit(AsyncIOEventEmitter):
    def __init__(self, channel_id, ice_servers=None):
        super().__init__()

        self.channel_id = channel_id
        self.ice_servers = ice_servers or []

        self.peers = {}
        self.peer_tracks: dict[str, list[TrackInfo]] = {}
        self.track_metadata: dict[str, TrackMetadata] = {}

        self.pending_renegotiation_tracks: dict[str, list[PendingTrack]] = {}
        self.inflight_renegotiation_tracks: dict[str, list[PendingTrack]] = {}
        self.renegotiate_tracks_tasks = {}

        self.media_relay = MediaRelay()

    def _cancel_renegotiation(self, sid):
        existing_task = self.renegotiate_tracks_tasks.pop(sid, None)
        if existing_task is not None:
            existing_task.cancel()

    def destroy(self):
        self.emit('status-changed')

    def _schedule_renegotiation(self, sid):
        self._cancel_renegotiation(sid)
        self.renegotiate_tracks_tasks[sid] = asyncio.create_task(self._renegotiate_tracks_for_sid(sid))

    async def _on_new_track_from_sid(self, from_sid, new_track):
        log.info(f'sfu: received {new_track.kind} track from {from_sid}')

        track_id = str(uuid.uuid4())[:8]
        self.track_metadata[track_id] = TrackMetadata(sid=from_sid, kind=new_track.kind)

        source_tracks = self.peer_tracks.setdefault(from_sid, [])
        source_tracks.append(TrackInfo(track=new_track, track_id=track_id, kind=new_track.kind))

        for relay_sid in list(self.peers.keys()):
            if from_sid == relay_sid:
                continue

            relay_pc = self.peers[relay_sid]
            if relay_pc.connectionState == 'closed':
                continue

            pending_tracks = self.pending_renegotiation_tracks.setdefault(relay_sid, [])
            pending_tracks.append(PendingTrack(peer_id=from_sid, track=new_track, track_id=track_id))
            self._schedule_renegotiation(relay_sid)

    async def _renegotiate_tracks_for_sid(self, sid):
        await asyncio.sleep(0.1)

        pc = self.peers.get(sid)
        if not pc:
            return

        # wait for any in-progress negotiation to finish before starting a new one
        while pc.signalingState != 'stable':
            await asyncio.sleep(0.1)
            if sid not in self.peers or pc.signalingState == 'closed':
                return

        pending_tracks = self.pending_renegotiation_tracks.pop(sid, [])
        if not pending_tracks:
            return

        # move pending → inflight so tracks arriving between now and the client's
        # answer don't get mixed into this renegotiation round
        self.inflight_renegotiation_tracks[sid] = pending_tracks

        renegotiation_entries = [
            RenegotiationEntry(
                peer_id=pending_track.peer_id, kind=pending_track.track.kind, track_id=pending_track.track_id
            )
            for pending_track in pending_tracks
        ]

        self.emit('renegotiate', sid, renegotiation_entries)

    async def handle_offer(self, offering_sid, sdp, sdp_type):
        log.info(f'sfu:on_offer from {offering_sid}')
        offer = aiortc.RTCSessionDescription(sdp, sdp_type)

        pc = self.peers.get(offering_sid)
        if pc is not None:
            # existing connection — renegotiation
            track_count_before = len(self.peer_tracks.get(offering_sid, []))
            await pc.setRemoteDescription(offer)

            all_transceivers = pc.getTransceivers()
            inflight_tracks = self.inflight_renegotiation_tracks.pop(offering_sid, [])

            if inflight_tracks:
                # client added recvonly transceivers at the tail; flip to sendonly for relay
                target_transceivers = all_transceivers[-len(inflight_tracks) :]

                for i, inflight_track in enumerate(inflight_tracks):
                    relay = self.media_relay.subscribe(inflight_track.track, buffered=False)
                    if i < len(target_transceivers):
                        # aiortc bug: direction/_offerDirection are wrong for incoming transceivers
                        target_transceivers[i].direction = 'sendonly'
                        target_transceivers[i]._offerDirection = 'sendonly'
                        target_transceivers[i].sender.replaceTrack(relay)
                    else:
                        log.warning(f'sfu:on_offer no target transceiver for relay track {i} to {offering_sid}')

                log.info(f'sfu:on_offer added {len(inflight_tracks)} relay tracks for existing peer {offering_sid}')

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            new_tracks = self.peer_tracks.get(offering_sid, [])[track_count_before:]
            return OfferResult(description=pc.localDescription, new_tracks=new_tracks)

        # new connection

        ice_servers = [
            aiortc.RTCIceServer(
                urls=s.get('urls', ''),
                username=s.get('username'),
                credential=s.get('credential'),
            )
            for s in self.ice_servers
        ]
        rtc_configuration = aiortc.RTCConfiguration(iceServers=ice_servers) if ice_servers else None
        pc = aiortc.RTCPeerConnection(configuration=rtc_configuration)
        self.peers[offering_sid] = pc

        @pc.on('track')
        async def on_track(track):
            await self._on_new_track_from_sid(offering_sid, track)

        track_count_before = len(self.peer_tracks.get(offering_sid, []))
        await pc.setRemoteDescription(offer)
        await pc.setLocalDescription(await pc.createAnswer())

        if offering_sid not in self.peers:
            log.info(f'sfu:on_offer peer {offering_sid} left during ICE gathering, discarding answer')
            return None

        log.info(f'sfu:on_offer created answer for {offering_sid}')
        log.debug(f'sfu:on_offer answer SDP for {offering_sid}:\n{pc.localDescription.sdp}')

        # queue existing peers' tracks for renegotiation to the new peer, skipping
        # any already queued by _on_new_track_from_sid (race when peers join simultaneously);
        # check both pending and inflight — debounce may have fired during ICE gathering
        already_pending = self.pending_renegotiation_tracks.get(offering_sid, [])
        already_inflight = self.inflight_renegotiation_tracks.get(offering_sid, [])
        already_queued_track_ids = {id(pt.track) for pt in already_pending} | {id(pt.track) for pt in already_inflight}

        for existing_sid in self.peer_tracks:
            if offering_sid == existing_sid:
                continue

            tracks_to_add = [
                PendingTrack(peer_id=existing_sid, track=track_info.track, track_id=track_info.track_id)
                for track_info in self.peer_tracks.get(existing_sid, [])
                if id(track_info.track) not in already_queued_track_ids
            ]

            if tracks_to_add:
                pending_tracks = self.pending_renegotiation_tracks.setdefault(offering_sid, [])
                pending_tracks.extend(tracks_to_add)

        if self.pending_renegotiation_tracks.get(offering_sid):
            log.info(
                f'sfu:on_offer {len(self.pending_renegotiation_tracks[offering_sid])} relay tracks pending for {offering_sid}, requesting renegotiation'
            )
            self._schedule_renegotiation(offering_sid)

        self.emit('status-changed')

        new_tracks = self.peer_tracks.get(offering_sid, [])[track_count_before:]
        return OfferResult(description=pc.localDescription, new_tracks=new_tracks)

    async def handle_ice_candidate(self, sid, candidate_data):
        pc = self.peers.get(sid)
        if not pc:
            return

        if candidate_data is None:
            await pc.addIceCandidate(None)
            return

        candidate_str = candidate_data.get('candidate', '')
        if not candidate_str:
            return

        try:
            aioice_candidate = AioIceCandidate.from_sdp(candidate_str)
            rtc_candidate = candidate_from_aioice(aioice_candidate)
            rtc_candidate.sdpMid = candidate_data.get('sdpMid')
            rtc_candidate.sdpMLineIndex = candidate_data.get('sdpMLineIndex')
            await pc.addIceCandidate(rtc_candidate)
        except Exception as e:
            log.warning(f'sfu:ice-candidate failed to add candidate for {sid}: {e}')

    async def remove_peer(self, sid):
        log.info(f'sfu:remove_peer removing {sid} from channel {self.channel_id}')

        self._cancel_renegotiation(sid)

        pc = self.peers.pop(sid, None)
        if pc is not None:
            await pc.close()

        self.peer_tracks.pop(sid, None)
        self.pending_renegotiation_tracks.pop(sid, None)
        self.inflight_renegotiation_tracks.pop(sid, None)

        # purge departed peer's tracks from other peers' pending queues
        for other_sid in list(self.pending_renegotiation_tracks.keys()):
            self.pending_renegotiation_tracks[other_sid] = [
                pt for pt in self.pending_renegotiation_tracks[other_sid] if pt.peer_id != sid
            ]

        # clean up track metadata owned by this peer
        owned_track_ids = [tid for tid, meta in self.track_metadata.items() if meta.sid == sid]
        for tid in owned_track_ids:
            del self.track_metadata[tid]

        self.emit('status-changed')

    def handle_track_kill(self, track_id):
        meta = self.track_metadata.pop(track_id, None)
        if not meta:
            return

        source_tracks = self.peer_tracks.get(meta.sid, [])
        self.peer_tracks[meta.sid] = [t for t in source_tracks if t.track_id != track_id]

    def is_empty(self):
        return len(self.peers) == 0
