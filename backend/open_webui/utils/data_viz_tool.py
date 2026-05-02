"""
Built-in Data Visualization tool for Open WebUI.

The `show_widget` tool ferries an HTML/SVG fragment to the frontend, which
renders it inside a sandboxed iframe. The tool itself does no rendering — it
asks the frontend (via `__event_call__`, which round-trips a Socket.IO event
and awaits the response) to render and report status. If the iframe throws a
runtime error, the tool re-prompts the model for a corrected fragment and
loops up to N attempts before giving up.

The tool's return string is the only signal the model sees about render
outcome — it's set ONCE, after the loop concludes, and never modified
retroactively. Possible final results:

  - "Widget '<title>' rendered."
  - "Widget '<title>' rendered. Your code errored and was auto-fixed. Changes: <summary>."
  - "Widget '<title>' rendered (no client confirmation)."  # render timed out
  - "ERROR: widget '<title>' threw <msg>"                  # unrecoverable; no
                                                           # auto-repair mention,
                                                           # so the model can
                                                           # naturally retry on
                                                           # its own without
                                                           # being confused by a
                                                           # system it doesn't
                                                           # know about.

If a repair was applied, the tool also emits an `embeds` event carrying the
final corrected `widget_code`, keyed on a hash of the ORIGINAL `widget_code`.
On reload, the frontend hashes the broken `arguments.widget_code` and looks up
the override so it renders the working version without re-running the repair.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from typing import Any, Awaitable, Callable, List, Optional

from fastapi import Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.data_viz_repair import call_repair_model


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# How long we wait for the frontend to confirm a render. If the user closes
# the tab or the socket dies, we fail-soft: return "rendered (no confirmation)"
# instead of stalling the model indefinitely.
RENDER_TIMEOUT_S = 30.0


def _override_key(widget_code: str) -> str:
    """Stable key for matching reload-time renders against persisted overrides.
    Hash of the ORIGINAL (pre-repair) widget_code so the frontend can look up
    by hashing whatever's in arguments.widget_code on the persisted message."""
    h = hashlib.sha256(widget_code.encode("utf-8", errors="replace"))
    return h.hexdigest()[:16]


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
        __event_call__: Optional[Callable[[dict], Awaitable[Any]]] = None,
        __event_emitter__: Optional[Callable[[dict], Awaitable[Any]]] = None,
        __metadata__: Optional[dict] = None,
        __model__: Optional[dict] = None,
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
            A string describing the final render outcome.
        """
        log.info(f"DATA VIZ: show_widget title={title!r} code_len={len(widget_code)}")

        original_code = widget_code
        original_key = _override_key(original_code)

        # No socket round-trip available (e.g., direct API call without a
        # frontend session): fall back to a best-effort success report. The
        # widget will render whenever a frontend eventually loads the chat.
        if __event_call__ is None or __request__ is None:
            return f"Widget '{title}' rendered."

        cfg = __request__.app.state.config
        auto_repair_enabled = bool(getattr(cfg, "DATA_VIZ_AUTO_REPAIR_ENABLED", True))
        max_attempts = max(1, min(int(getattr(cfg, "DATA_VIZ_AUTO_REPAIR_MAX_ATTEMPTS", 3)), 5))

        original_model_id: Optional[str] = None
        if isinstance(__model__, dict):
            original_model_id = __model__.get("id")

        code = original_code
        summary_chunks: list[str] = []
        attempts = 0  # number of repair attempts performed

        while True:
            request_id = str(uuid.uuid4())
            payload = {
                "type": "data_viz:render",
                "data": {
                    "request_id": request_id,
                    "override_key": original_key,
                    "title": title,
                    "widget_code": code,
                    "attempt": attempts,
                    "is_repair": attempts > 0,
                    "loading_messages": loading_messages or [],
                },
            }

            try:
                resp = await asyncio.wait_for(
                    __event_call__(payload), timeout=RENDER_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                log.info("data_viz: render timed out (request_id=%s)", request_id)
                # Persist any in-progress fix so reload uses the latest attempt.
                if attempts > 0:
                    await _emit_override(__event_emitter__, original_key, code)
                return f"Widget '{title}' rendered (no client confirmation)."
            except Exception:
                log.exception("data_viz: __event_call__ raised")
                return f"Widget '{title}' rendered (client unreachable)."

            if not isinstance(resp, dict):
                # Older frontends or odd responses — assume success.
                resp = {"status": "ok"}

            status = resp.get("status")

            if status == "ok":
                if attempts > 0:
                    await _emit_override(__event_emitter__, original_key, code)
                    summary = "; ".join(s for s in summary_chunks if s) or "auto-repaired"
                    return (
                        f"Widget '{title}' rendered. Your code errored and was "
                        f"auto-fixed. Changes: {summary}."
                    )
                return f"Widget '{title}' rendered."

            # status == "error" (or anything unrecognized — treat as error).
            error_message = (resp.get("error_message") or "unknown error").strip()
            error_stack = resp.get("error_stack") or None

            if not auto_repair_enabled or attempts >= max_attempts:
                # Don't mention auto-repair in the error string — the model would
                # get confused about a system it doesn't know it's part of, and
                # the natural next step is for the model to emit show_widget again
                # with a fix. Just give it the raw error.
                return f"ERROR: widget '{title}' threw {error_message[:300]}"

            # Run a repair attempt.
            attempts += 1
            log.info(
                "data_viz: invoking repair model attempt=%s err=%r",
                attempts, error_message[:120],
            )
            repair = await call_repair_model(
                request=__request__,
                user=__user__,
                cfg=cfg,
                title=title,
                widget_code=code,
                error_message=error_message,
                error_stack=error_stack,
                original_model_id=original_model_id,
                attempt=attempts,
            )

            if not repair or not repair.get("widget_code"):
                return f"ERROR: widget '{title}' threw {error_message[:300]}"

            code = repair["widget_code"]
            if repair.get("summary"):
                summary_chunks.append(repair["summary"])
            # Loop: send the new code and wait for the next render outcome.


async def _emit_override(
    emit: Optional[Callable[[dict], Awaitable[Any]]],
    key: str,
    widget_code: str,
) -> None:
    """Persist the corrected widget_code on the assistant message so reload
    renders the working version without re-running the repair. Uses a
    dedicated event type (not `embeds`, which the frontend renders as iframes
    inline below the message)."""
    if emit is None:
        return
    try:
        await emit(
            {
                "type": "data_viz:override",
                "data": {"key": key, "widget_code": widget_code},
            }
        )
    except Exception:
        log.exception("data_viz: failed to emit override event")


_data_viz_tools_instance: Optional[DataVizTools] = None


def get_data_viz_tools_instance() -> DataVizTools:
    """Get or create the singleton DataVizTools instance."""
    global _data_viz_tools_instance
    if _data_viz_tools_instance is None:
        _data_viz_tools_instance = DataVizTools()
    return _data_viz_tools_instance
