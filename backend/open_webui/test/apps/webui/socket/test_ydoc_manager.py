import pytest
from open_webui.socket.utils import YdocManager


class FakeAsyncRedis:
    def __init__(self):
        self.sets = {}
        self.lists = {}

    async def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(values)

    async def srem(self, key, *values):
        if key not in self.sets:
            return 0

        removed = 0
        for value in values:
            if value in self.sets[key]:
                self.sets[key].remove(value)
                removed += 1
        return removed

    async def smembers(self, key):
        return set(self.sets.get(key, set()))

    async def scard(self, key):
        return len(self.sets.get(key, set()))

    async def rpush(self, key, *values):
        self.lists.setdefault(key, []).extend(values)

    async def llen(self, key):
        return len(self.lists.get(key, []))

    async def lrange(self, key, start, end):
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]

    async def exists(self, key):
        return int(key in self.sets or key in self.lists)

    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            deleted += int(self.sets.pop(key, None) is not None)
            deleted += int(self.lists.pop(key, None) is not None)
        return deleted

    def scan_iter(self, *args, **kwargs):
        raise AssertionError('YdocManager should use the per-user document index instead of scanning all documents')


@pytest.mark.asyncio
async def test_remove_user_from_all_documents_uses_reverse_index():
    redis = FakeAsyncRedis()
    manager = YdocManager(redis=redis, redis_key_prefix='test:ydoc')

    await manager.add_user('note:owned', 'sid-1')
    await manager.add_user('note:shared', 'sid-1')
    await manager.add_user('note:shared', 'sid-2')
    await manager.append_to_updates('note:owned', b'owned-update')
    await manager.append_to_updates('note:shared', b'shared-update')

    await manager.remove_user_from_all_documents('sid-1')

    assert await manager.get_users('note:shared') == ['sid-2']
    assert await manager.document_exists('note:shared') is True
    assert await manager.document_exists('note:owned') is False
    assert await redis.smembers('test:ydoc:users:sid-1:documents') == set()
    assert await redis.smembers('test:ydoc:users:sid-2:documents') == {'note_shared'}


@pytest.mark.asyncio
async def test_clear_document_removes_document_from_user_indexes():
    redis = FakeAsyncRedis()
    manager = YdocManager(redis=redis, redis_key_prefix='test:ydoc')

    await manager.add_user('note:shared', 'sid-1')
    await manager.add_user('note:shared', 'sid-2')
    await manager.append_to_updates('note:shared', b'shared-update')

    await manager.clear_document('note:shared')

    assert await manager.document_exists('note:shared') is False
    assert await redis.smembers('test:ydoc:users:sid-1:documents') == set()
    assert await redis.smembers('test:ydoc:users:sid-2:documents') == set()
