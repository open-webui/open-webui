"""
Default prompt scaffolding for the Data Visualization feature.

These constants are intentionally empty on a fresh install. The admin pastes the
real prompt text into the admin UI (Admin Settings > Data Visualization), and
PersistentConfig writes those values to the DB. The constants here are just
defaults the config falls back to before any admin override exists.
"""

SHARED_CORE: str = ""
MODULE_DIAGRAM: str = ""
MODULE_MOCKUP_INTERACTIVE: str = ""
MODULE_CHART_DATAVIZ: str = ""
MODULE_ART: str = ""
MODULE_ELICITATION: str = ""


def assemble_data_viz_system_prompt(config) -> str:
    """
    Assemble the data visualization system prompt from the live config object.

    Concatenates the shared core prompt + each enabled module's prompt. Empty
    sections are skipped so we never inject blank whitespace. If nothing is
    enabled (or all sections are empty), returns "" and the caller should skip
    injection entirely.
    """
    parts: list[str] = []

    shared_core = (getattr(config, "DATA_VIZ_SHARED_CORE_PROMPT", "") or "").strip()
    if shared_core:
        parts.append(shared_core)

    modules = (
        ("DIAGRAM", "DATA_VIZ_MODULE_DIAGRAM"),
        ("MOCKUP_INTERACTIVE", "DATA_VIZ_MODULE_MOCKUP_INTERACTIVE"),
        ("CHART_DATAVIZ", "DATA_VIZ_MODULE_CHART_DATAVIZ"),
        ("ART", "DATA_VIZ_MODULE_ART"),
        ("ELICITATION", "DATA_VIZ_MODULE_ELICITATION"),
    )
    for _label, prefix in modules:
        enabled = getattr(config, f"{prefix}_ENABLED", False)
        prompt = (getattr(config, f"{prefix}_PROMPT", "") or "").strip()
        if enabled and prompt:
            parts.append(prompt)

    return "\n\n".join(parts)
