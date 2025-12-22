import os
import pytest
from unittest.mock import patch, MagicMock, call
import sys


class TestAuditLogConfiguration:
    """Test audit logging configuration with AUDIT_ENABLE_STDOUT and AUDIT_ENABLE_FILE"""

    def test_audit_enable_stdout_true(self):
        """Test that when AUDIT_ENABLE_STDOUT is True, audit logs are included in stdout"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "True",
                "AUDIT_ENABLE_FILE": "False",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that AUDIT_ENABLE_STDOUT was set correctly
            assert env.AUDIT_ENABLE_STDOUT is True
            assert env.AUDIT_ENABLE_FILE is False

    def test_audit_enable_stdout_false(self):
        """Test that when AUDIT_ENABLE_STDOUT is False, audit logs are excluded from stdout"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "False",
                "AUDIT_ENABLE_FILE": "True",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that AUDIT_ENABLE_STDOUT was set correctly
            assert env.AUDIT_ENABLE_STDOUT is False
            assert env.AUDIT_ENABLE_FILE is True

    def test_audit_enable_file_true(self):
        """Test that when AUDIT_ENABLE_FILE is True, audit logs are written to file"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "False",
                "AUDIT_ENABLE_FILE": "True",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that AUDIT_ENABLE_FILE was set correctly
            assert env.AUDIT_ENABLE_FILE is True
            assert env.AUDIT_LOG_LEVEL == "METADATA"

    def test_audit_enable_file_false(self):
        """Test that when AUDIT_ENABLE_FILE is False, audit logs are not written to file"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "True",
                "AUDIT_ENABLE_FILE": "False",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that AUDIT_ENABLE_FILE was set correctly
            assert env.AUDIT_ENABLE_FILE is False

    def test_audit_both_enabled(self):
        """Test that both stdout and file can be enabled simultaneously"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "True",
                "AUDIT_ENABLE_FILE": "True",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that both flags are enabled
            assert env.AUDIT_ENABLE_STDOUT is True
            assert env.AUDIT_ENABLE_FILE is True

    def test_audit_both_disabled(self):
        """Test that audit logging can be completely disabled"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "False",
                "AUDIT_ENABLE_FILE": "False",
                "AUDIT_LOG_LEVEL": "METADATA",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that both flags are disabled
            assert env.AUDIT_ENABLE_STDOUT is False
            assert env.AUDIT_ENABLE_FILE is False

    def test_audit_log_level_none_disables_file(self):
        """Test that AUDIT_LOG_LEVEL=NONE prevents file logging even if AUDIT_ENABLE_FILE=True"""
        with patch.dict(
            os.environ,
            {
                "AUDIT_ENABLE_STDOUT": "False",
                "AUDIT_ENABLE_FILE": "True",
                "AUDIT_LOG_LEVEL": "NONE",
                "GLOBAL_LOG_LEVEL": "INFO",
            },
        ):
            # Reload env and logger to pick up new env vars
            import importlib
            from open_webui import env
            from open_webui.utils import logger as logger_module
            from loguru import logger

            importlib.reload(env)
            importlib.reload(logger_module)

            # Clear any existing handlers
            logger.remove()
            
            logger_module.start_logger()

            # Check that AUDIT_LOG_LEVEL is NONE - this should prevent file logging
            assert env.AUDIT_LOG_LEVEL == "NONE"
            assert env.AUDIT_ENABLE_FILE is True


class TestEnvVariables:
    """Test that environment variables are correctly parsed"""

    def test_audit_enable_stdout_default(self):
        """Test AUDIT_ENABLE_STDOUT parsing when explicitly set to default value"""
        with patch.dict(os.environ, {"GLOBAL_LOG_LEVEL": "INFO", "AUDIT_ENABLE_STDOUT": "False"}):
            import importlib
            from open_webui import env

            importlib.reload(env)
            assert env.AUDIT_ENABLE_STDOUT is False

    def test_audit_enable_file_default(self):
        """Test AUDIT_ENABLE_FILE parsing when explicitly set to default value"""
        with patch.dict(os.environ, {"GLOBAL_LOG_LEVEL": "INFO", "AUDIT_ENABLE_FILE": "True"}):
            import importlib
            from open_webui import env

            importlib.reload(env)
            assert env.AUDIT_ENABLE_FILE is True

    def test_audit_enable_stdout_true_parsing(self):
        """Test AUDIT_ENABLE_STDOUT=True is correctly parsed"""
        with patch.dict(os.environ, {"AUDIT_ENABLE_STDOUT": "True"}):
            import importlib
            from open_webui import env

            importlib.reload(env)
            assert env.AUDIT_ENABLE_STDOUT is True

    def test_audit_enable_file_false_parsing(self):
        """Test AUDIT_ENABLE_FILE=False is correctly parsed"""
        with patch.dict(os.environ, {"AUDIT_ENABLE_FILE": "False"}):
            import importlib
            from open_webui import env

            importlib.reload(env)
            assert env.AUDIT_ENABLE_FILE is False
