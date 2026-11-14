"""Native coding agent support for Open Terminal environments."""


def reasoning_effort(options):
    params = options.get('params') or {}
    params = {**params, **(params.get('custom_params') or {})}
    value = params.get('reasoningEffort') or params.get('reasoning_effort')
    return value.strip() if isinstance(value, str) and value.strip() else None
