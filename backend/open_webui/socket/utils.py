import json
import uuid
import logging
from open_webui.utils.redis import get_redis_connection
from open_webui.env import REDIS_KEY_PREFIX
from typing import List
from pyee.asyncio import AsyncIOEventEmitter
import pycrdt as Y
import asyncio
import aiortc
from aiortc.contrib.media import MediaRelay
from aiortc.rtcicetransport import candidate_from_aioice
from aioice.candidate import Candidate as AioIceCandidate

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


class SelectiveForwardingUnit(AsyncIOEventEmitter):
    """SFU (Selective Forwarding Unit) — a server-side WebRTC relay that receives each
    peer's media tracks and selectively forwards them to every other peer in the call,
    avoiding the O(n^2) mesh of direct peer-to-peer connections."""

    def __init__(self, channel_id, ice_servers=None):
        super().__init__()

        self.channel_id = channel_id
        self.ice_servers = ice_servers or []

        self.peers = {}
        self.peer_tracks = {}

        self.pending_renegotiation_tracks = {}
        self.inflight_renegotiation_tracks = {}
        self.renegotiate_tracks_tasks = {}

        self.media_relay = MediaRelay()

    def _make_rtc_configuration(self):
        servers = [
            aiortc.RTCIceServer(
                urls=s.get('urls', ''),
                username=s.get('username'),
                credential=s.get('credential'),
            )
            for s in self.ice_servers
        ]
        return aiortc.RTCConfiguration(iceServers=servers) if servers else None

    async def _on_new_track_from_sid(self, from_sid, new_track):
        log.info(f'sfu:_on_new_track_from_sid received {new_track.kind} track from {from_sid}')

        # add track to sid's current tracks
        from_sid_current_tracks = self.peer_tracks.setdefault(from_sid, [])
        from_sid_current_tracks.append(new_track)

        # iterate over all peers and consider this track for renegotiation
        for relay_sid in list(self.peers.keys()):
            # don't relay this track to the sender
            if from_sid == relay_sid:
                continue

            relay_pc = self.peers[relay_sid]
            if relay_pc.connectionState == 'closed':
                continue

            pending_tracks = self.pending_renegotiation_tracks.setdefault(relay_sid, [])
            pending_tracks.append({'peer_id': from_sid, 'track': new_track})

            # emit the renegotiation task once even if n tracks come in quick succession
            # i.e., emit 100ms after receiving a track; if another comes in, cancel and reschedule
            existing_renegotiation_task = self.renegotiate_tracks_tasks.pop(relay_sid, None)
            if existing_renegotiation_task is not None:
                existing_renegotiation_task.cancel()

            self.renegotiate_tracks_tasks[relay_sid] = asyncio.create_task(self._renegotiate_tracks_for_sid(relay_sid))

    async def _renegotiate_tracks_for_sid(self, sid):
        await asyncio.sleep(0.1)

        pc = self.peers.get(sid)
        if not pc:
            log.info(f'sfu:renegotiate no pc for {sid}, skipping')
            return

        # if signaling state is not stable, then a previous negotiation is in process;
        # wait until it is complete before starting a new renegotiation
        while pc.signalingState != 'stable':
            log.info(f'sfu:renegotiate waiting for stable state for {sid} (current: {pc.signalingState})')

            await asyncio.sleep(0.1)

            if sid not in self.peers or pc.signalingState == 'closed':
                return

        pending_tracks = self.pending_renegotiation_tracks.pop(sid, [])
        if not pending_tracks:
            return

        # move the tracks from pending to inflight, as the client must generate an offer with transceivers;
        # should new tracks be added between this renegotiate event and an answer, we should only add the inflight tracks
        self.inflight_renegotiation_tracks[sid] = pending_tracks

        data = [{'peer_id': row.get('peer_id'), 'kind': row.get('track').kind} for row in pending_tracks]

        self.emit('renegotiate', sid, data)

    async def handle_offer(self, offering_sid, sdp, sdp_type):
        log.info(f'sfu:on_offer from {offering_sid}')
        offer = aiortc.RTCSessionDescription(sdp, sdp_type)

        # existing connection: track renegotiation
        pc = self.peers.get(offering_sid)
        if pc is not None:
            await pc.setRemoteDescription(offer)

            inflight_peer_tracks = self.inflight_renegotiation_tracks.pop(offering_sid, [])
            new_tracks = [row.get('track') for row in inflight_peer_tracks]

            if new_tracks:
                all_transceivers = pc.getTransceivers()

                # client added recvonly transceivers at the tail of the SDP; flip them to sendonly so we can push relay tracks
                target_transceivers = all_transceivers[-len(new_tracks) :]

                for i, track in enumerate(new_tracks):
                    relay = self.media_relay.subscribe(track, buffered=False)
                    if i < len(target_transceivers):
                        # aiortc incorrectly sets direction and _offerDirection for incoming transceivers; override both
                        target_transceivers[i].direction = 'sendonly'
                        target_transceivers[i]._offerDirection = 'sendonly'
                        target_transceivers[i].sender.replaceTrack(relay)
                    else:
                        log.warning(f'sfu:on_offer no target transceiver for relay track {i} to {offering_sid}')

                log.info(f'sfu:on_offer added {len(new_tracks)} relay tracks for existing peer {offering_sid}')

            # return answer to renegotiation offer
            await pc.setLocalDescription(await pc.createAnswer())
            return pc.localDescription

        # new connection

        pc = aiortc.RTCPeerConnection(configuration=self._make_rtc_configuration())
        self.peers[offering_sid] = pc

        @pc.on('track')
        async def on_track(track):
            await self._on_new_track_from_sid(offering_sid, track)

        # complete the initial handshake without the other peers' tracks
        await pc.setRemoteDescription(offer)
        await pc.setLocalDescription(await pc.createAnswer())

        # peer may have been removed while awaiting TURN/ICE gathering
        if offering_sid not in self.peers:
            log.info(f'sfu:on_offer peer {offering_sid} left during ICE gathering, discarding answer')
            return None

        log.info(f'sfu:on_offer created answer for {offering_sid}')
        log.debug(f'sfu:on_offer answer SDP for {offering_sid}:\n{pc.localDescription.sdp}')

        # prepare other peers' tracks for renegotiation, skipping any already queued
        # by _on_new_track_from_sid (race when multiple peers join simultaneously)
        already_pending = self.pending_renegotiation_tracks.get(offering_sid, [])
        already_pending_tracks = {id(row['track']) for row in already_pending}

        for existing_sid in self.peer_tracks:
            if offering_sid == existing_sid:
                continue

            new_tracks = [
                {'peer_id': existing_sid, 'track': track}
                for track in self.peer_tracks.get(existing_sid, [])
                if id(track) not in already_pending_tracks
            ]

            if new_tracks:
                pending_tracks = self.pending_renegotiation_tracks.setdefault(offering_sid, [])
                pending_tracks.extend(new_tracks)

        # if the above block generated pending tracks, schedule a renegotiation task
        if self.pending_renegotiation_tracks.get(offering_sid):
            log.info(
                f'sfu:on_offer {len(self.pending_renegotiation_tracks[offering_sid])} relay tracks pending for {offering_sid}, requesting renegotiation'
            )
            # cancel any existing task from _on_new_track_from_sid to avoid duplicate renegotiation events
            existing_task = self.renegotiate_tracks_tasks.pop(offering_sid, None)
            if existing_task is not None:
                existing_task.cancel()

            self.renegotiate_tracks_tasks[offering_sid] = asyncio.create_task(
                self._renegotiate_tracks_for_sid(offering_sid)
            )

        # return answer for offer
        return pc.localDescription

    async def handle_ice_candidate(self, sid, candidate_data):
        pc = self.peers.get(sid)
        if not pc:
            return

        if candidate_data is None:
            # end-of-candidates signal
            await pc.addIceCandidate(None)
            log.info(f'sfu:ice-candidate end-of-candidates for {sid}')
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
            log.info(f'sfu:ice-candidate added {rtc_candidate.type} candidate for {sid}')
        except Exception as e:
            log.warning(f'sfu:ice-candidate failed to add candidate for {sid}: {e}')

    async def remove_peer(self, sid):
        log.info(f'sfu:remove_peer removing {sid} from channel {self.channel_id}')

        existing_renegotiation_task = self.renegotiate_tracks_tasks.pop(sid, None)
        if existing_renegotiation_task is not None:
            existing_renegotiation_task.cancel()

        existing_pc = self.peers.pop(sid, None)
        if existing_pc is not None:
            await existing_pc.close()

        self.peer_tracks.pop(sid, None)
        self.pending_renegotiation_tracks.pop(sid, None)
        self.inflight_renegotiation_tracks.pop(sid, None)

    def is_empty(self):
        return len(self.peers) == 0
