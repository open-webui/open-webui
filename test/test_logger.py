from unittest.mock import Mock

from open_webui.utils import logger as logger_module


def test_start_logger_disables_loguru_diagnose_for_stdout(monkeypatch):
    add = Mock(return_value=1)

    monkeypatch.setattr(logger_module, 'LOG_FORMAT', '')
    monkeypatch.setattr(logger_module, 'AUDIT_LOG_LEVEL', 'NONE')
    monkeypatch.setattr(logger_module.logger, 'add', add)
    monkeypatch.setattr(logger_module.logger, 'remove', Mock())
    monkeypatch.setattr(logger_module.logger, 'info', Mock())

    logger_module.start_logger()

    stdout_sink = add.call_args_list[0]
    assert stdout_sink.kwargs['diagnose'] is False
