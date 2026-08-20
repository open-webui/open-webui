# tasks.py
import asyncio
import logging
import time
from contextlib import suppress
from copy import deepcopy
from uuid import uuid4

from redis.asyncio import Redis

from open_webui.env import REDIS_KEY_PREFIX, REDIS_RESPONSE_STREAM_TTL
from open_webui.utils.json_codec import JSONCodec, dumps_bytes
from open_webui.utils.misc import get_output_text, sanitize_text_for_db

log = logging.getLogger(__name__)

# A dictionary to keep track of active tasks
tasks: dict[str, asyncio.Task] = {}
item_tasks = {}
response_streams: dict[str, dict] = {}


REDIS_TASKS_KEY = f'{REDIS_KEY_PREFIX}:tasks'
REDIS_ITEM_TASKS_KEY = f'{REDIS_KEY_PREFIX}:tasks:item'
REDIS_RESPONSE_STREAMS_KEY = f'{REDIS_KEY_PREFIX}:tasks:response_streams'
# lane before id: a client-supplied id must not collide with another stream's key
REDIS_RESPONSE_STREAM_KEY_PREFIX = f'{REDIS_KEY_PREFIX}:tasks:response_stream'
REDIS_PUBSUB_CHANNEL = f'{REDIS_KEY_PREFIX}:tasks:commands'
REDIS_PUBSUB_RECONNECT_INTERVAL = 1.0
REDIS_PUBSUB_MAX_RECONNECT_INTERVAL = 30.0

RESPONSE_STREAM_EXPIRE_SECONDS = REDIS_RESPONSE_STREAM_TTL if REDIS_RESPONSE_STREAM_TTL > 0 else None

# TTL refresh cadence; also bounds how long an evicted ledger key goes unnoticed
RESPONSE_STREAM_EXPIRE_REFRESH_SECONDS = (
    min(10, RESPONSE_STREAM_EXPIRE_SECONDS / 2) if RESPONSE_STREAM_EXPIRE_SECONDS else 10
)

# Append growth outside the journaled leaf is rewritten in batches of at least this size
RESPONSE_STREAM_DRIFT_REWRITE_CHARS = 4096

# Per-process incremental-writer state for in-flight response streams, keyed by task id
_stream_states: dict[str, dict] = {}

# Sentinel distinguishing "structures differ" from "no difference" in _grown_leaves
_DIFFERS = object()

# Marks a slot whose field does not exist in the hash yet; None is not usable
# as the marker because output items themselves may legally be None
_UNWRITTEN = object()


def _ledger_key(task_id: str) -> str:
    return f'{REDIS_RESPONSE_STREAM_KEY_PREFIX}:ledger:{task_id}'


def _content_key(task_id: str) -> str:
    return f'{REDIS_RESPONSE_STREAM_KEY_PREFIX}:content:{task_id}'


def _journal_key(task_id: str) -> str:
    return f'{REDIS_RESPONSE_STREAM_KEY_PREFIX}:journal:{task_id}'


def _queue_stream_key_deletes(pipe, task_id: str):
    # separate deletes: the three keys hash to different cluster slots
    pipe.delete(_ledger_key(task_id))
    pipe.delete(_content_key(task_id))
    pipe.delete(_journal_key(task_id))
    # previous-release writers still use the global hash; drop with the next release
    pipe.hdel(REDIS_RESPONSE_STREAMS_KEY, task_id)


def _new_stream_state() -> dict:
    return {
        'slots': [],  # one slot per output item
        'next_field': 0,
        'saved_order': None,  # fkey list as last written into the meta field
        'saved_journal': None,  # [fkey, leaf path, nonce] of the active journal
        'journal_bytes': 0,  # server-side byte length of the journal value
        'content': '',
        'content_bytes': 0,  # server-side byte length of the content value
        # keys are armed at creation, so the first probe is due one refresh later
        'expire_after': time.monotonic() + RESPONSE_STREAM_EXPIRE_REFRESH_SECONDS,
    }


async def redis_task_command_listener(app):
    redis: Redis = app.state.redis
    reconnect_interval = REDIS_PUBSUB_RECONNECT_INTERVAL

    while True:
        pubsub = None
        try:
            pubsub = redis.pubsub()
            await pubsub.subscribe(REDIS_PUBSUB_CHANNEL)
            reconnect_interval = REDIS_PUBSUB_RECONNECT_INTERVAL

            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                try:
                    command = JSONCodec.loads(message['data'])
                    if command.get('action') != 'stop':
                        continue

                    local_task = tasks.get(command.get('task_id'))
                    if local_task:
                        local_task.cancel()
                except Exception as e:
                    log.exception(f'Error handling distributed task command: {e}')
            log.warning('Redis task command listener stopped. Retrying.')
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception(f'Redis task command listener failed. Retrying: {e}')
        finally:
            if pubsub:
                with suppress(Exception):
                    await pubsub.aclose()

        await asyncio.sleep(reconnect_interval)
        reconnect_interval = min(reconnect_interval * 2, REDIS_PUBSUB_MAX_RECONNECT_INTERVAL)


### ------------------------------
### REDIS-ENABLED HANDLERS
### ------------------------------


async def redis_save_task(redis: Redis, task_id: str, item_id: str | None):
    pipe = redis.pipeline()
    pipe.hset(REDIS_TASKS_KEY, task_id, item_id or '')
    if item_id:
        pipe.sadd(f'{REDIS_ITEM_TASKS_KEY}:{item_id}', task_id)
    await pipe.execute()


async def redis_cleanup_task(redis: Redis, task_id: str, item_id: str | None):
    pipe = redis.pipeline()
    pipe.hdel(REDIS_TASKS_KEY, task_id)
    _queue_stream_key_deletes(pipe, task_id)
    if item_id:
        pipe.srem(f'{REDIS_ITEM_TASKS_KEY}:{item_id}', task_id)
        await pipe.execute()
        # Remove the set key entirely if no tasks remain for this item
        if await redis.scard(f'{REDIS_ITEM_TASKS_KEY}:{item_id}') == 0:
            await redis.delete(f'{REDIS_ITEM_TASKS_KEY}:{item_id}')
    else:
        await pipe.execute()


async def redis_list_tasks(redis: Redis) -> list[str]:
    return list(await redis.hkeys(REDIS_TASKS_KEY))


async def redis_list_item_tasks(redis: Redis, item_id: str) -> list[str]:
    return list(await redis.smembers(f'{REDIS_ITEM_TASKS_KEY}:{item_id}'))


async def redis_send_command(redis: Redis, command: dict):
    command_json = dumps_bytes(command)
    # RedisCluster doesn't expose publish() directly, but the
    # PUBLISH command broadcasts across all cluster nodes server-side.
    if hasattr(redis, 'nodes_manager'):
        await redis.execute_command('PUBLISH', REDIS_PUBSUB_CHANNEL, command_json)
    else:
        await redis.publish(REDIS_PUBSUB_CHANNEL, command_json)


async def cleanup_task(redis, task_id: str, id=None):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    # local state first: it must go even when Redis is unreachable
    tasks.pop(task_id, None)  # Remove the task if it exists
    response_streams.pop(task_id, None)
    _stream_states.pop(task_id, None)

    # If an ID is provided, remove the task from the item_tasks dictionary
    if id and task_id in item_tasks.get(id, []):
        item_tasks[id].remove(task_id)
        if not item_tasks[id]:  # If no tasks left for this ID, remove the entry
            item_tasks.pop(id, None)

    if redis:
        await redis_cleanup_task(redis, task_id, id)


async def create_task(redis, coroutine, id=None, task_id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = task_id or str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

    # Add a done callback for cleanup
    task.add_done_callback(lambda t: asyncio.create_task(cleanup_task(redis, task_id, id)))
    tasks[task_id] = task

    # If an ID is provided, associate the task with that ID
    if item_tasks.get(id):
        item_tasks[id].append(task_id)
    else:
        item_tasks[id] = [task_id]

    if redis:
        await redis_save_task(redis, task_id, id)

    return task_id, task


async def list_tasks(redis):
    """
    List all currently active task IDs.
    """
    if redis:
        return await redis_list_tasks(redis)
    return list(tasks.keys())


async def list_task_ids_by_item_id(redis, id):
    """
    List all tasks associated with a specific ID.
    """
    if redis:
        return await redis_list_item_tasks(redis, id)
    return item_tasks.get(id, [])


def _rewrite_budget(item_json_chars: int) -> int:
    # scales with the item's serialized size so batch rewrites amortize to O(new content)
    return max(RESPONSE_STREAM_DRIFT_REWRITE_CHARS, item_json_chars // 4)


def _grown_leaves(previous, current, path=()):  # noqa: C901
    """Compare two JSON structures; return None when identical, a list of
    (path, grown chars) when every difference is a string leaf growing by
    appending, _DIFFERS otherwise."""
    if isinstance(previous, str) and isinstance(current, str):
        if previous == current:
            return None
        if len(current) > len(previous) and current.startswith(previous):
            return [(path, len(current) - len(previous))]
        return _DIFFERS
    if isinstance(previous, dict) and isinstance(current, dict):
        if list(previous.keys()) != list(current.keys()):
            return _DIFFERS
        pairs = [(previous[key], current[key], key) for key in current]
    elif isinstance(previous, list) and isinstance(current, list):
        if len(previous) != len(current):
            return _DIFFERS
        pairs = [(p, c, index) for index, (p, c) in enumerate(zip(previous, current))]
    else:
        # type-sensitive equality: True == 1 must not count as identical
        if type(previous) is type(current) and previous == current:
            return None
        return _DIFFERS

    found = []
    for child_previous, child_current, step in pairs:
        result = _grown_leaves(child_previous, child_current, path + (step,))
        if result is None:
            continue
        if result is _DIFFERS:
            return _DIFFERS
        found.extend(result)
    return found or None


def _set_leaf(node, path, value):
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value


def _leaf_value(node, path):
    for step in path:
        node = node[step]
    return node


def _total_growth(grown, skip=None):
    return sum(growth for path, growth in grown if path != skip)


def _item_id(item):
    # output is user-editable via the chats API: items may not be dicts, ids may not be str
    item_id = item.get('id') if isinstance(item, dict) else None
    return item_id if isinstance(item_id, str) else None


def _choose_journal_slot(slots, diffs, appendable, journal_ref):
    """The journal follows growth, not position: it stays on its item while that
    item keeps appending and moves to the biggest grower once it goes quiet.
    A demoted slot's diff is set to _DIFFERS in place so it rewrites in full
    (its field lags the journal). Returns (journal_ref, journaled fkey)."""
    if journal_ref:
        for index, slot in enumerate(slots):
            if slot['fkey'] != journal_ref[0]:
                continue
            bound_diff = diffs[index]
            if bound_diff is _DIFFERS or (bound_diff is None and appendable):
                diffs[index] = _DIFFERS
                break
            return journal_ref, journal_ref[0]
        # falling out of the loop means the bound item was realigned away
    if appendable:
        return None, max(appendable, key=lambda fkey: _total_growth(appendable[fkey]))
    return None, None


def _collect_changed_fields(slots, output, journal_ref):
    """Serialize every item whose content changed. Returns the dirty fields,
    how many of them are new, the journal op and the updated journal ref."""
    diffs = [
        _DIFFERS if slot['snapshot'] is _UNWRITTEN else _grown_leaves(slot['snapshot'], item)
        for slot, item in zip(slots, output)
    ]

    growing = {slot['fkey']: diff for slot, diff in zip(slots, diffs) if isinstance(diff, list)}
    # a root-level string leaf has an empty path and cannot be journaled
    appendable = {fkey: diff for fkey, diff in growing.items() if all(path for path, _ in diff)}
    journal_ref, target_fkey = _choose_journal_slot(slots, diffs, appendable, journal_ref)

    fields = {}
    new_fields = 0
    journal = None
    for slot, item, diff in zip(slots, output, diffs):
        fkey = slot['fkey']
        if diff is None:
            continue
        if fkey == target_fkey:
            write_field, journal, journal_ref = _diff_journal_item(slot, journal_ref, item, appendable[fkey])
            if not write_field:
                continue
        elif fkey in growing and _total_growth(growing[fkey]) <= _rewrite_budget(slot['item_json_chars']):
            # non-journaled append growth defers under the geometric budget
            continue

        if slot['snapshot'] is _UNWRITTEN:
            new_fields += 1
        fields[fkey] = JSONCodec.dumps(item)
        slot['snapshot'] = deepcopy(item)
        slot['item_json_chars'] = len(fields[fkey])

    return fields, new_fields, journal, journal_ref


def _is_rendered(path):
    # the lanes structuredOutput.ts renders as message text
    return len(path) == 3 and path[0] in ('content', 'summary') and path[2] == 'text'


def _journal_leaf(grown, item):
    """Pick the leaf to journal: prefer what the UI renders (content and summary
    text lanes) over larger unrendered twins such as reasoning_details."""
    rendered = [leaf_path for leaf_path, _ in grown if _is_rendered(leaf_path)]
    candidates = rendered or [leaf_path for leaf_path, _ in grown]
    return max(candidates, key=lambda p: len(_leaf_value(item, p)))


def _diff_journal_item(slot, journal_ref, item, grown):
    """Decide how to persist the journaled item. Returns
    (write_field, journal op, journal_ref)."""
    preferred = _journal_leaf(grown, item)

    journal = None
    if journal_ref is None:
        text = _leaf_value(item, preferred)
        journal = ('set', text)
        journal_ref = [slot['fkey'], preferred, uuid4().hex]
        _set_leaf(slot['snapshot'], preferred, text)
    else:
        if _is_rendered(preferred) and not _is_rendered(journal_ref[1]):
            # a rendered lane started growing while an unrendered one holds the
            # journal: rewrite in full so the next save re-binds to it
            return True, None, None
        growth = next((growth for leaf_path, growth in grown if leaf_path == journal_ref[1]), 0)
        if not growth and preferred != journal_ref[1]:
            # the bound leaf idles while another grows: rewrite in full, re-bind next save
            return True, None, None
        # growth > 0 here: the idle case returned above
        leaf = _leaf_value(item, journal_ref[1])
        journal = ('append', leaf[len(leaf) - growth :])
        _set_leaf(slot['snapshot'], journal_ref[1], leaf)

    drift = _total_growth(grown, skip=journal_ref[1])
    if drift > _rewrite_budget(slot['item_json_chars']):
        if preferred != journal_ref[1]:
            # a better leaf outranks the journaled one: drop the journal
            # with the full write so the next save re-binds it
            return True, None, None
        return True, journal, journal_ref
    return False, journal, journal_ref


def _realign_slots(state, output):
    previous_slots = state['slots']
    by_obj_id = {id(slot['item']): index for index, slot in enumerate(previous_slots)}
    matched = set()
    slots = [None] * len(output)
    for position, item in enumerate(output):
        index = by_obj_id.get(id(item))
        if index is not None and index not in matched:
            matched.add(index)
            slots[position] = previous_slots[index]

    by_item_id = {}
    for index, slot in enumerate(previous_slots):
        if index not in matched:
            item_id = _item_id(slot['item'])
            if item_id is not None:
                by_item_id.setdefault(item_id, []).append(index)
    for position, item in enumerate(output):
        if slots[position] is not None:
            continue
        candidates = by_item_id.get(_item_id(item))
        if candidates:
            index = candidates.pop(0)
            matched.add(index)
            slots[position] = previous_slots[index]
        else:
            slots[position] = {
                'fkey': f'i{state["next_field"]}',
                'item': None,
                'snapshot': _UNWRITTEN,
                'item_json_chars': 0,
            }
            state['next_field'] += 1

    state['slots'] = slots
    return [slot['fkey'] for index, slot in enumerate(previous_slots) if index not in matched]


async def _refresh_ttls(redis, state, task_id) -> bool:
    """Periodic TTL refresh that doubles as the key-loss probe."""
    if time.monotonic() < state['expire_after']:
        return True
    keys = [_ledger_key(task_id)]
    if state['content']:
        keys.append(_content_key(task_id))
    if state['saved_journal']:
        keys.append(_journal_key(task_id))
    for key in keys:  # separate calls: the keys hash to different cluster slots
        if RESPONSE_STREAM_EXPIRE_SECONDS:
            alive = await redis.expire(key, RESPONSE_STREAM_EXPIRE_SECONDS)
        else:
            alive = await redis.exists(key)
        if not alive:
            return False
    state['expire_after'] = time.monotonic() + RESPONSE_STREAM_EXPIRE_REFRESH_SECONDS
    return True


async def _write_stream(redis, state, task_id, chat_id, message_id, content, output) -> bool:  # noqa: C901
    """One incremental persistence pass. False means the server state no longer
    matches the local mirror and the stream must be rebuilt."""
    ledger_key = _ledger_key(task_id)
    content_key = _content_key(task_id)
    journal_key = _journal_key(task_id)

    orphans = []
    if len(state['slots']) != len(output):
        orphans = _realign_slots(state, output)
    slots = state['slots']

    fields, new_fields, journal, journal_ref = _collect_changed_fields(slots, output, state['saved_journal'])
    for slot, item in zip(slots, output):
        slot['item'] = item  # pin: keeps id(item) unique while the slot lives

    order = [slot['fkey'] for slot in slots]
    if order != state['saved_order'] or journal_ref != state['saved_journal']:
        if state['saved_order'] is None:
            new_fields += 1
        fields['meta'] = JSONCodec.dumps(
            {'v': 1, 'chat_id': chat_id, 'message_id': message_id, 'order': order, 'journal': journal_ref}
        )

    # text lanes first: a torn read then sees newer text, never older;
    # stripped like the DB convention, raw lanes would raise on strict UTF-8
    if journal is not None:
        kind, text = journal
        if kind == 'set':
            journal_value = f'{journal_ref[2]}:{sanitize_text_for_db(text)}'
            await redis.set(journal_key, journal_value, ex=RESPONSE_STREAM_EXPIRE_SECONDS)
            state['journal_bytes'] = len(journal_value.encode('utf-8'))
        else:
            journal_suffix = sanitize_text_for_db(text)
            expected = state['journal_bytes'] + len(journal_suffix.encode('utf-8'))
            if await redis.append(journal_key, journal_suffix) != expected:
                return False
            state['journal_bytes'] = expected

    previous = state['content']
    if content != previous:
        state['content'] = content
        if previous and content.startswith(previous):
            # per-code-point stripping distributes over concatenation
            suffix = sanitize_text_for_db(content[len(previous) :])
            expected = state['content_bytes'] + len(suffix.encode('utf-8'))
            if await redis.append(content_key, suffix) != expected:
                return False
            state['content_bytes'] = expected
        else:
            sanitized = sanitize_text_for_db(content)
            await redis.set(content_key, sanitized, ex=RESPONSE_STREAM_EXPIRE_SECONDS)
            state['content_bytes'] = len(sanitized.encode('utf-8'))

    if fields:
        if RESPONSE_STREAM_EXPIRE_SECONDS and state['saved_order'] is None:
            # one packet: a kill between HSET and EXPIRE would leak an unexpiring key
            pipe = redis.pipeline()
            pipe.hset(ledger_key, mapping=fields)
            pipe.expire(ledger_key, RESPONSE_STREAM_EXPIRE_SECONDS)
            added = (await pipe.execute())[0]
        else:
            added = await redis.hset(ledger_key, mapping=fields)
        if added != new_fields:
            return False
        state['saved_order'] = order
        state['saved_journal'] = journal_ref
    if orphans:
        # after the HSET: the new meta no longer names these fields
        await redis.hdel(ledger_key, *orphans)

    return await _refresh_ttls(redis, state, task_id)


async def save_response_stream(
    redis,
    task_id: str | None,
    chat_id: str | None,
    message_id: str | None,
    content: str,
    output: list,
):
    if not task_id or not chat_id or not message_id:
        return

    if not redis:
        response_streams[task_id] = {
            'chat_id': chat_id,
            'message_id': message_id,
            'content': content,
            'output': output,
        }
        return

    state = _stream_states.get(task_id)
    if state is None:
        state = _stream_states[task_id] = _new_stream_state()

    try:
        if await _write_stream(redis, state, task_id, chat_id, message_id, content, output):
            return
        log.info(f'Response stream {task_id} for chat {chat_id} state out of sync, rebuilding')
        state = _stream_states[task_id] = _new_stream_state()
        pipe = redis.pipeline()
        _queue_stream_key_deletes(pipe, task_id)
        await pipe.execute()
        if await _write_stream(redis, state, task_id, chat_id, message_id, content, output):
            return
    except BaseException:
        # the local mirror may be ahead of Redis: drop it and re-prove next save
        _stream_states.pop(task_id, None)
        raise
    # even the rebuild failed (e.g. a concurrent cleanup): start clean next save
    _stream_states.pop(task_id, None)
    log.warning(
        f'Response stream {task_id} for chat {chat_id} was not persisted this save, retrying from scratch next save'
    )


async def _load_stream(redis, task_id: str, fields: dict) -> dict | None:
    for is_retry in (False, True):
        try:
            meta = JSONCodec.loads(fields['meta'])
            if meta.get('v') != 1:
                # written by a newer release during a rolling upgrade
                log.debug(f'Response stream {task_id} skipped: unknown layout version')
                return None
            output = [JSONCodec.loads(fields[fkey]) for fkey in meta['order']]
            journal_ref = meta.get('journal')
            if journal_ref:
                fkey, path, nonce = journal_ref
                journal = await redis.get(_journal_key(task_id))
                marker, _, text = (journal or '').partition(':')
                if marker != nonce:
                    # the journal was rewritten between our HGETALL and GET: re-read once
                    if is_retry:
                        log.debug(f'Response stream {task_id} skipped: journal nonce mismatch')
                        return None
                    fields = await redis.hgetall(_ledger_key(task_id))
                    if not fields:
                        log.debug(f'Response stream {task_id} skipped: ledger gone during retry')
                        return None
                    continue
                _set_leaf(output[meta['order'].index(fkey)], path, text)
            content = await redis.get(_content_key(task_id))
            return {
                'chat_id': meta.get('chat_id'),
                'message_id': meta.get('message_id'),
                'content': content or get_output_text(output),
                'output': output,
            }
        except (KeyError, ValueError, IndexError, TypeError, AttributeError):
            # torn or partially cleaned-up write: skip rather than render a wrong snapshot
            log.debug(f'Response stream {task_id} skipped: torn or partial write', exc_info=True)
            return None


async def _gather_ledger_streams(redis, chat_id: str, task_ids: list[str]) -> tuple[list[dict], list[str]]:
    """Load the new-format overlays; returns (streams, task ids without a ledger)."""
    ledgers = await asyncio.gather(
        *(redis.hgetall(_ledger_key(task_id)) for task_id in task_ids), return_exceptions=True
    )
    with_ledger = []
    legacy_task_ids = []
    for task_id, fields in zip(task_ids, ledgers):
        if isinstance(fields, BaseException):
            log.warning(f'Response stream {task_id} overlay skipped for chat {chat_id}', exc_info=fields)
        elif fields:
            with_ledger.append((task_id, fields))
        else:
            legacy_task_ids.append(task_id)

    loaded = await asyncio.gather(
        *(_load_stream(redis, task_id, fields) for task_id, fields in with_ledger),
        return_exceptions=True,
    )
    streams = []
    for (task_id, _), stream in zip(with_ledger, loaded):
        if isinstance(stream, BaseException):
            log.warning(f'Response stream {task_id} overlay unreadable for chat {chat_id}', exc_info=stream)
        elif stream and stream.get('chat_id') == chat_id:
            streams.append(stream)
    return streams, legacy_task_ids


async def get_response_streams_by_chat_id(redis, chat_id: str) -> list[dict]:
    if not redis:
        return [
            stream
            for task_id in await list_task_ids_by_item_id(redis, chat_id)
            if (stream := response_streams.get(task_id)) and stream.get('chat_id') == chat_id
        ]

    try:
        task_ids = await list_task_ids_by_item_id(redis, chat_id)
        if not task_ids:
            return []
        streams, legacy_task_ids = await _gather_ledger_streams(redis, chat_id, task_ids)

        if legacy_task_ids:
            # streams written by processes still running the previous release
            try:
                for value in await redis.hmget(REDIS_RESPONSE_STREAMS_KEY, legacy_task_ids):
                    if not value:
                        continue
                    try:
                        data = JSONCodec.loads(value)
                    except Exception:
                        continue
                    if data.get('chat_id') == chat_id:
                        streams.append(data)
            except Exception:
                # the legacy hash lives on its own slot: its loss must not drop the rest
                log.warning(f'Legacy response stream overlay unavailable for chat {chat_id}', exc_info=True)
        return streams
    except Exception:
        # the overlay is cosmetic: a Redis hiccup must not fail the whole chat load
        log.warning(f'Response stream overlay unavailable for chat {chat_id}', exc_info=True)
        return []


async def clear_response_stream(redis, task_id: str | None):
    if not task_id:
        return
    _stream_states.pop(task_id, None)
    if redis:
        pipe = redis.pipeline()
        _queue_stream_key_deletes(pipe, task_id)
        await pipe.execute()
    else:
        response_streams.pop(task_id, None)


async def stop_task(redis, task_id: str):
    """
    Cancel a running task and remove it from the global task list.
    """
    if redis:
        # Look up the item_id before cleanup so we can remove the set entry too
        item_id = await redis.hget(REDIS_TASKS_KEY, task_id)
        # PUBSUB: All instances check if they have this task, and stop if so.
        await redis_send_command(
            redis,
            {
                'action': 'stop',
                'task_id': task_id,
            },
        )
        # Always clean Redis directly — hdel/srem are idempotent, safe even
        # if the done_callback on the owning process also fires cleanup.
        await redis_cleanup_task(redis, task_id, item_id or None)
        return {'status': True, 'message': f'Task {task_id} stopped.'}

    task = tasks.pop(task_id, None)
    if not task:
        return {'status': False, 'message': f'Task with ID {task_id} not found.'}

    task.cancel()  # Request task cancellation
    try:
        await task  # Wait for the task to handle the cancellation
    except asyncio.CancelledError:
        # Task successfully canceled
        return {'status': True, 'message': f'Task {task_id} successfully stopped.'}

    if task.cancelled() or task.done():
        return {'status': True, 'message': f'Task {task_id} successfully cancelled.'}

    return {'status': True, 'message': f'Cancellation requested for {task_id}.'}


async def stop_item_tasks(redis: Redis, item_id: str):
    """
    Stop all tasks associated with a specific item ID.
    """
    task_ids = await list_task_ids_by_item_id(redis, item_id)
    if not task_ids:
        return {'status': True, 'message': f'No tasks found for item {item_id}.'}

    for task_id in task_ids:
        result = await stop_task(redis, task_id)
        if not result['status']:
            return result  # Return the first failure

    return {'status': True, 'message': f'All tasks for item {item_id} stopped.'}


async def has_active_tasks(redis, chat_id: str) -> bool:
    """Check if a chat has any active tasks."""
    task_ids = await list_task_ids_by_item_id(redis, chat_id)
    return len(task_ids) > 0
