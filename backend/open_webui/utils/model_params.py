def _dump_model_params(model_info) -> dict:
    params = getattr(model_info, 'params', None)
    if not params:
        return {}

    if hasattr(params, 'model_dump'):
        return params.model_dump()

    return dict(params)


def pop_model_params_from_payload(payload: dict, model_info=None) -> dict:
    payload_params = payload.pop('params', None) or {}
    if not isinstance(payload_params, dict):
        payload_params = {}

    return {
        **_dump_model_params(model_info),
        **payload_params,
    }
