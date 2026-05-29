## Summary
- honor model params stored under `meta.params` as well as `params`
- also honor `model_item.info.meta.params` from the request payload
- fixes MCP/native function calling being silently ignored for some model edit paths

## Root cause
Open WebUI computes `model_info_params` from `Model.params`, but the frontend/request path can carry settings like `function_calling: native` under `model_item.info.meta.params`. In that case the backend ignores the setting and falls back to non-native tool handling.

This showed up as MCP tools being selected in the UI but not being passed through correctly to the model.

## Test plan
- reproduced with Open WebUI + MCP tool server selected
- observed request payload containing `model_item.info.meta.params.function_calling = "native"`
- confirmed backend ignored that value before this patch
- patched running container with the same change and verified the issue was resolved
