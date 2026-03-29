"""Client-facing realtime defaults and capability data."""


from typing import Any

from open_webui.realtime.catalog import build_voice_capabilities
from open_webui.realtime.config_snapshot import (
    build_realtime_client_defaults,
    resolve_realtime_model_ids,
)
from open_webui.realtime.constants import (
    REALTIME_NOISE_REDUCTION_TYPES,
    REALTIME_SEMANTIC_VAD_EAGERNESS,
    REALTIME_VAD_TYPES,
)


def build_realtime_client_config(request: Any) -> dict[str, Any]:
    config = request.app.state.config
    enabled = config.AUDIO_RT_ENGINE == "openai" and bool(config.AUDIO_RT_API_KEY)

    model_ids = resolve_realtime_model_ids(
        config,
        getattr(request.app.state, "MODELS", None),
    )

    return {
        "enabled": enabled,
        "defaults": build_realtime_client_defaults(config),
        "capabilities": {
            "models": model_ids,
            **build_voice_capabilities(model_ids),
            "vad_types": list(REALTIME_VAD_TYPES),
            "noise_reduction": list(REALTIME_NOISE_REDUCTION_TYPES),
            "semantic_vad_eagerness": list(REALTIME_SEMANTIC_VAD_EAGERNESS),
        },
    }
