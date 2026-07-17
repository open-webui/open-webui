from open_webui.utils.payload import resolve_system_prompt


async def resolve_model_system_prompt(
    model_info,  # ModelModel | None
    metadata: dict | None,
    user,
    *,
    bypass: bool = False,
) -> str:
    if bypass or model_info is None:
        return ''
    raw = None
    if model_info.params:
        raw = model_info.params.model_dump().get('system')
    return await resolve_system_prompt(raw, metadata, user)
