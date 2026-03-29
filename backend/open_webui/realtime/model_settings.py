"""Helpers for reading saved model settings in realtime flows."""


from open_webui.models.models import Models


def get_realtime_model_system_prompt(model_id: str) -> str:
    """Resolve the saved model-level system prompt for a realtime session."""
    model = Models.get_model_by_id(model_id)
    if not model:
        return ""

    params = model.params.model_dump() if model.params else {}
    system_prompt = params.get("system")
    return system_prompt if isinstance(system_prompt, str) else ""
