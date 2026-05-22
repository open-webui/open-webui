import sys
import types

# Stub lightweight dependencies that misc.py imports at module level so tests
# can run without a full application bootstrap.
_env = types.ModuleType('open_webui.env')
_env.CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE = 16384
sys.modules.setdefault('open_webui.env', _env)
sys.modules.setdefault('mimeparse', types.ModuleType('mimeparse'))
sys.modules.setdefault('aiohttp', types.ModuleType('aiohttp'))

from open_webui.utils.misc import sanitize_data_for_db  # noqa: E402


class TestSanitizeDataForDb:
    def test_string_null_bytes_removed(self):
        assert sanitize_data_for_db('a\x00b') == 'ab'

    def test_dict_value_null_bytes_removed(self):
        result = sanitize_data_for_db({'key': 'val\x00ue'})
        assert result == {'key': 'value'}

    def test_nested_dict_value_null_bytes_removed(self):
        result = sanitize_data_for_db({'a': {'b': 'c\x00'}})
        assert result == {'a': {'b': 'c'}}

    def test_list_value_null_bytes_removed(self):
        result = sanitize_data_for_db(['a\x00', {'b': 'c\x00'}])
        assert result == ['a', {'b': 'c'}]

    def test_clean_data_returned_unchanged(self):
        data = {'key': 'value', 'items': ['a', 'b'], 'num': 42}
        assert sanitize_data_for_db(data) is data
