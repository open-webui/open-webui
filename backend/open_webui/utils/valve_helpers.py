"""
Valve helper utilities for Functions and Tools to update their own valves.
"""

import logging
from open_webui.models.functions import Functions
from open_webui.models.tools import Tools

log = logging.getLogger(__name__)


def update_function_valves(function_id: str, valve_updates: dict) -> bool:
    """
    Update function valves from within the function itself.

    Args:
        function_id: The ID of the function
        valve_updates: Dictionary of valve updates to apply

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        current_valves = Functions.get_function_valves_by_id(function_id)
        if current_valves is None:
            current_valves = {}
        updated_valves = {**current_valves, **valve_updates}
        Functions.update_function_valves_by_id(function_id, updated_valves)
        return True
    except Exception as e:
        log.exception(
            f"Error updating function valves from within function {function_id}: {e}"
        )
        return False


def update_tool_valves(tool_id: str, valve_updates: dict) -> bool:
    """
    Update tool valves from within the tool itself.

    Args:
        tool_id: The ID of the tool
        valve_updates: Dictionary of valve updates to apply

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        current_valves = Tools.get_tool_valves_by_id(tool_id) or {}
        updated_valves = {**current_valves, **valve_updates}
        Tools.update_tool_valves_by_id(tool_id, updated_valves)
        return True
    except Exception as e:
        log.exception(f"Error updating tool valves from within tool {tool_id}: {e}")
        return False


def get_function_valves(function_id: str) -> dict:
    """
    Get current function valves from within the function itself.

    Args:
        function_id: The ID of the function

    Returns:
        dict: Current valve values
    """
    try:
        return Functions.get_function_valves_by_id(function_id) or {}
    except Exception as e:
        log.exception(
            f"Error getting function valves from within function {function_id}: {e}"
        )
        return {}


def get_tool_valves(tool_id: str) -> dict:
    """
    Get current tool valves from within the tool itself.

    Args:
        tool_id: The ID of the tool

    Returns:
        dict: Current valve values
    """
    try:
        return Tools.get_tool_valves_by_id(tool_id) or {}
    except Exception as e:
        log.exception(f"Error getting tool valves from within tool {tool_id}: {e}")
        return {}
