"""MCP app result data and sandbox policy."""

import hmac
import re
from dataclasses import dataclass

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.json_codec import JSONCodec

APP_MIME_TYPE = 'text/html;profile=mcp-app'
MAX_APP_BYTES = 5 * 1024 * 1024
_DOMAIN = re.compile(r'(?:https?|wss?)://(?:\*\.)?(?:[a-zA-Z0-9.-]+|\[[a-fA-F0-9:]+\])(?::[0-9]{1,5})?')


@dataclass
class MCPAppResult:
    embed: dict
    context: list[dict]


def app_binding(server_id: str, tool_name: str) -> str:
    # Bind callbacks to a server/tool; the endpoint separately authenticates the viewer.
    if not WEBUI_SECRET_KEY:
        raise ValueError('A stable WEBUI_SECRET_KEY is required for MCP apps')
    payload = JSONCodec.dumps([server_id, tool_name], ensure_ascii=True).encode()
    return hmac.digest(WEBUI_SECRET_KEY.encode(), b'open-webui-mcp-app-v1\n' + payload, 'sha256').hex()


def verify_app_binding(server_id: str, tool_name: str, binding: str) -> bool:
    return bool(WEBUI_SECRET_KEY) and hmac.compare_digest(app_binding(server_id, tool_name), binding)


def ui_metadata(value: dict) -> dict:
    meta = value.get('_meta') or {}
    ui = meta.get('ui') if isinstance(meta, dict) else None
    return ui if isinstance(ui, dict) else {}


def ui_resource_uri(tool: dict) -> str | None:
    meta = tool.get('_meta') or {}
    if not isinstance(meta, dict):
        return None
    uri = ui_metadata(tool).get('resourceUri') or meta.get('ui/resourceUri')
    return uri if isinstance(uri, str) and uri.startswith('ui://') else None


def app_csp(ui: dict) -> str:
    csp = ui.get('csp') or {}
    if not isinstance(csp, dict):
        raise ValueError('Invalid app CSP')

    def domains(key):
        values = csp.get(key, [])
        if not isinstance(values, list) or any(
            not isinstance(value, str)
            or not _DOMAIN.fullmatch(value)
            or (key != 'connectDomains' and not value.startswith(('https://', 'http://')))
            for value in values
        ):
            raise ValueError('Invalid app CSP domain')
        return ' '.join(values)

    resources = domains('resourceDomains')
    deny = "'none'"
    return '; '.join(
        [
            "default-src 'none'",
            f"script-src 'unsafe-inline' blob: {resources}",
            f"style-src 'unsafe-inline' {resources}",
            f'img-src data: blob: {resources}',
            f'media-src data: blob: {resources}',
            f'font-src {resources or deny}',
            f'connect-src {domains("connectDomains") or deny}',
            f'frame-src {domains("frameDomains") or deny}',
            f'base-uri {domains("baseUriDomains") or deny}',
            "object-src 'none'",
            "form-action 'none'",
        ]
    )
