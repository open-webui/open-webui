"""Shared constants and capability helpers for realtime chat."""


USER_TRANSCRIBING_PLACEHOLDER = "*Transcribing...*"
ASSISTANT_LISTENING_PLACEHOLDER = "*Listening...*"

OPENAI_REALTIME_MODERN_VOICES = (
    "alloy",
    "ash",
    "ballad",
    "cedar",
    "coral",
    "echo",
    "marin",
    "sage",
    "shimmer",
    "verse",
)

OPENAI_REALTIME_LEGACY_VOICES = (
    "alloy",
    "echo",
    "fable",
    "nova",
    "onyx",
    "shimmer",
)

ALL_REALTIME_VOICES = tuple(
    dict.fromkeys((*OPENAI_REALTIME_MODERN_VOICES, *OPENAI_REALTIME_LEGACY_VOICES))
)

REALTIME_VAD_TYPES = ("semantic_vad", "server_vad", "push_to_talk")
REALTIME_NOISE_REDUCTION_TYPES = ("near_field", "far_field", "")
REALTIME_SEMANTIC_VAD_EAGERNESS = ("low", "medium", "high", "auto")


def get_realtime_voice_ids_for_model(model_id: str) -> tuple[str, ...]:
    """Return the supported voice identifiers for a realtime-capable model."""
    normalized_model_id = (model_id or "").lower()
    if normalized_model_id.startswith("gpt-realtime"):
        return OPENAI_REALTIME_MODERN_VOICES

    if normalized_model_id.startswith("gpt-4o") and "realtime" in normalized_model_id:
        return ALL_REALTIME_VOICES

    return ALL_REALTIME_VOICES
