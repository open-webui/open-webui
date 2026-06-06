import importlib.util
import sys
import types
from pathlib import Path


def _load_logger_module(monkeypatch):
    env = types.ModuleType('open_webui.env')
    env._LEVEL_MAP = {}
    env.AUDIT_LOG_FILE_ROTATION_SIZE = '10 MB'
    env.AUDIT_LOG_LEVEL = 'NONE'
    env.AUDIT_LOGS_FILE_PATH = 'audit.log'
    env.AUDIT_UVICORN_LOGGER_NAMES = []
    env.ENABLE_AUDIT_LOGS_FILE = False
    env.ENABLE_AUDIT_STDOUT = False
    env.ENABLE_OTEL = False
    env.ENABLE_OTEL_LOGS = False
    env.GLOBAL_LOG_LEVEL = 'INFO'
    env.LOG_FORMAT = ''

    package = types.ModuleType('open_webui')
    package.__path__ = []
    monkeypatch.setitem(sys.modules, 'open_webui', package)
    monkeypatch.setitem(sys.modules, 'open_webui.env', env)

    logger_path = Path(__file__).parents[1] / 'backend/open_webui/utils/logger.py'
    spec = importlib.util.spec_from_file_location('test_logger_module', logger_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_text_logs_do_not_include_exception_frame_values(monkeypatch, capsys):
    logger_module = _load_logger_module(monkeypatch)
    secret = 'test-api-key-that-must-not-be-logged'

    def raise_request_error(_request):
        raise RuntimeError('request failed')

    def send_request():
        http_request = {'headers': {'x-api-key': secret}}
        raise_request_error(http_request)

    logger_module.start_logger()
    try:
        try:
            send_request()
        except RuntimeError:
            logger_module.logger.exception('Upstream request failed')

        output = capsys.readouterr().out
        assert 'send_request' in output
        assert 'RuntimeError: request failed' in output
        assert secret not in output
    finally:
        logger_module.logger.remove()
