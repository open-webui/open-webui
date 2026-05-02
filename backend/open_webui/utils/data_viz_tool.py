"""
Built-in Data Visualization tool for Open WebUI.

Exposes a single function `show_widget` that the model calls to render a
visualization inline in the chat. The tool itself does no heavy work — the
widget content travels in the call's `arguments`, and the frontend mounts a
sandboxed iframe (or SVG container) directly from those arguments. The string
returned to the model is just an acknowledgment so the model can continue.
"""

import logging
from typing import List, Optional

from fastapi import Request
from pydantic import BaseModel

log = logging.getLogger(__name__)


class DataVizTools:
    """Built-in tool: show_widget(title, widget_code, loading_messages?)."""

    class Valves(BaseModel):
        """Configuration placeholder — settings are managed via the admin panel."""

        pass

    def __init__(self):
        self.valves = self.Valves()

    async def show_widget(
        self,
        title: str,
        widget_code: str,
        loading_messages: Optional[List[str]] = None,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Display a data visualization widget inline in the chat.

        The widget renders in a sandboxed iframe. Allowed external script CDNs:
        cdnjs.cloudflare.com, cdn.jsdelivr.net, esm.sh, unpkg.com. No
        localStorage/sessionStorage. No position: fixed (the iframe sizes to
        in-flow content height).

        Args:
            title: snake_case identifier. Used as the widget's download filename
                and accessibility label. Example: "power_functions_demo".
            widget_code: Raw HTML fragment OR raw SVG string. NOT a full
                document — do not include <!DOCTYPE>, <html>, <head>, or <body>
                tags. Mode is auto-detected: if it starts with "<svg", SVG mode;
                otherwise HTML mode.
            loading_messages: 1-4 short strings (~5 words each) shown while the
                widget mounts. Optional.

        Returns:
            A confirmation string for the model to continue from.
        """
        log.info(f"DATA VIZ: show_widget title={title!r} code_len={len(widget_code)}")
        return f"Widget '{title}' rendered."


_data_viz_tools_instance: Optional[DataVizTools] = None


def get_data_viz_tools_instance() -> DataVizTools:
    """Get or create the singleton DataVizTools instance."""
    global _data_viz_tools_instance
    if _data_viz_tools_instance is None:
        _data_viz_tools_instance = DataVizTools()
    return _data_viz_tools_instance
