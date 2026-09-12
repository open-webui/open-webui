def strip_provider_model_prefix(model_id: str, prefix_id: str | None) -> str:
    if prefix_id and model_id.startswith(f'{prefix_id}.'):
        return model_id[len(f'{prefix_id}.') :]
    return model_id
