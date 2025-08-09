"""
Logging utilities for Functions and Tools.
"""
import logging
import time
from typing import Optional

# Create a dedicated logger for functions and tools
function_tool_logger = logging.getLogger("open_webui.functions_tools")


class FunctionToolLogger:
    """Logger wrapper for Functions and Tools with enhanced functionality."""
    
    def __init__(self, module_type: str, module_id: str):
        self.module_type = module_type  # "function" or "tool"
        self.module_id = module_id
        self.logger = logging.getLogger(f"open_webui.{module_type}s.{module_id}")
        
    def _format_message(self, message: str, extra_data: Optional[dict] = None) -> str:
        """Format log message with module context."""
        prefix = f"[{self.module_type.upper()}:{self.module_id}]"
        if extra_data:
            extra_str = " | ".join([f"{k}={v}" for k, v in extra_data.items()])
            return f"{prefix} {message} | {extra_str}"
        return f"{prefix} {message}"
    
    def debug(self, message: str, extra_data: Optional[dict] = None):
        """Log debug message."""
        self.logger.debug(self._format_message(message, extra_data))
    
    def info(self, message: str, extra_data: Optional[dict] = None):
        """Log info message."""
        self.logger.info(self._format_message(message, extra_data))
    
    def warning(self, message: str, extra_data: Optional[dict] = None):
        """Log warning message."""
        self.logger.warning(self._format_message(message, extra_data))
    
    def error(self, message: str, extra_data: Optional[dict] = None):
        """Log error message."""
        self.logger.error(self._format_message(message, extra_data))
    
    def exception(self, message: str, extra_data: Optional[dict] = None):
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message, extra_data))
    
    def log_execution_time(self, func_name: str, start_time: float, extra_data: Optional[dict] = None):
        """Log function execution time."""
        execution_time = time.time() - start_time
        timing_data = {"execution_time_ms": round(execution_time * 1000, 2)}
        if extra_data:
            timing_data.update(extra_data)
        self.info(f"Function '{func_name}' executed", timing_data)
    
    def log_valve_update(self, valve_name: str, old_value, new_value):
        """Log valve updates."""
        self.info(f"Valve '{valve_name}' updated", {
            "old_value": str(old_value),
            "new_value": str(new_value)
        })
    
    def log_user_action(self, user_id: str, action: str, extra_data: Optional[dict] = None):
        """Log user actions."""
        action_data = {"user_id": user_id, "action": action}
        if extra_data:
            action_data.update(extra_data)
        self.info("User action logged", action_data)


def create_function_logger(function_id: str) -> FunctionToolLogger:
    """Create a logger for a function."""
    return FunctionToolLogger("function", function_id)


def create_tool_logger(tool_id: str) -> FunctionToolLogger:
    """Create a logger for a tool."""
    return FunctionToolLogger("tool", tool_id)