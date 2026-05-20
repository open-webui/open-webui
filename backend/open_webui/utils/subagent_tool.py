"""Built-in tools that let the parent chat model spawn research subagents.

The parent calls one of two tools:

- ``subagent_launch(name, prompt, background?)`` — spins up a fresh subagent in
  an isolated chat context, runs it to a natural stop (no tool calls in the
  final turn), and returns the synthesized final answer.

- ``subagent_continue(name_or_id, prompt)`` — resumes a previously-launched
  subagent with a follow-up turn so the parent can ask for elaboration without
  re-priming. The subagent keeps its full prior context (web pages it has
  already fetched, reasoning it has already done).

Both delegate to ``open_webui.utils.subagent``; this file only exists to
provide the OpenAI-function-shaped surface the parent model sees. The docstring
parsing in ``utils/tools.py`` (``parse_description`` + ``parse_docstring``)
turns these into the ``function`` block we send upstream as the tool spec.
Keep the descriptions short and the ``:param`` lines tight — they're what the
parent model reads when deciding whether to call.
"""

import logging
from typing import Callable, Optional

from fastapi import Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SubagentTools:
    """Builtin tool collection for parent-chat-spawned research subagents.

    Configuration (default model, system prompts, feature flag) is managed
    through the admin panel — see ``routers/subagents.py`` + ``config.py``.
    """

    class Valves(BaseModel):
        """Placeholder so the builtin-tool wiring stays consistent with the
        ``WebSearchTools`` pattern; no per-instance config to expose here."""
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def subagent_launch(
        self,
        name: str,
        prompt: str,
        background: str = "",
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
        __event_emitter__: Optional[Callable] = None,
        __event_call__: Optional[Callable] = None,
        __model__: Optional[dict] = None,
    ) -> str:
        """Spawn a research subagent that runs in its own isolated chat context with web search + fetch (and any tools the user enabled) and returns its synthesized final answer.

        :param name: Short snake_case identifier for this subagent (e.g. "berkeley_dorms"). Keep it short. Used to label the output and to reference the subagent later via subagent_continue.
        :param prompt: Detailed description of what to research. Be specific and thorough — the subagent only sees this, not our chat history.
        :param background: Optional context the subagent needs but can't infer from the prompt alone.
        :return: The subagent's final answer, prefixed with "Subagent N (name) output:".
        """
        from open_webui.utils.subagent import run_subagent_launch

        return await run_subagent_launch(
            request=__request__,
            user_dict=__user__,
            parent_metadata=__metadata__,
            parent_event_emitter=__event_emitter__,
            parent_event_call=__event_call__,
            parent_model=__model__,
            name=name,
            prompt=prompt,
            background=background,
        )

    async def subagent_continue(
        self,
        name_or_id: str,
        prompt: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
        __event_emitter__: Optional[Callable] = None,
        __event_call__: Optional[Callable] = None,
        __model__: Optional[dict] = None,
    ) -> str:
        """Continue a previously-launched subagent with a follow-up prompt. The subagent keeps its full prior context — use this to ask for elaboration or to do adjacent research without re-priming.

        :param name_or_id: Either the short name you gave the subagent at launch (most recent match if names collide), or its numeric id from the prior tool result.
        :param prompt: The follow-up question or instruction for the subagent.
        :return: The subagent's response after this continuation turn.
        """
        from open_webui.utils.subagent import run_subagent_continue

        return await run_subagent_continue(
            request=__request__,
            user_dict=__user__,
            parent_metadata=__metadata__,
            parent_event_emitter=__event_emitter__,
            parent_event_call=__event_call__,
            parent_model=__model__,
            name_or_id=name_or_id,
            prompt=prompt,
        )


_subagent_tools_instance: Optional[SubagentTools] = None


def get_subagent_tools_instance() -> SubagentTools:
    """Singleton accessor. Mirrors ``get_web_search_tools_instance``."""
    global _subagent_tools_instance
    if _subagent_tools_instance is None:
        _subagent_tools_instance = SubagentTools()
    return _subagent_tools_instance
