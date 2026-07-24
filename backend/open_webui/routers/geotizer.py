"""Authenticated download proxy for rendered GeoTeaser workbooks."""

from __future__ import annotations

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA,
)
from open_webui.utils.auth import get_verified_user
from open_webui.utils.tools import (
    build_tool_server_headers,
    get_tool_servers,
)

router = APIRouter()


@router.get('/files/{run_id}/geotizer.xlsx')
async def download_geotizer(
    run_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Proxy the private GIS artifact through the authenticated WebUI origin."""
    servers = await get_tool_servers(request)
    server = next(
        (item for item in servers if str(item.get('id')) == 'mcpgis'),
        None,
    )
    if server is None:
        raise HTTPException(503, 'GIS tool server is not configured')

    server_idx = int(server.get('idx', 0))
    connections = request.app.state.config.TOOL_SERVER_CONNECTIONS
    if server_idx >= len(connections):
        raise HTTPException(503, 'GIS tool server configuration is stale')
    connection = connections[server_idx]
    headers, cookies = await build_tool_server_headers(
        connection,
        request,
        user,
        server_id='mcpgis',
        metadata={'run_id': run_id},
    )
    url = f"{str(server.get('url') or '').rstrip('/')}" f"/geotizer/files/{run_id}/geotizer.xlsx"
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA)
        ) as session:
            async with session.get(
                url,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
            ) as upstream:
                body = await upstream.read()
                if upstream.status >= 400:
                    detail = body.decode('utf-8', errors='replace')[:500]
                    raise HTTPException(upstream.status, detail)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            502,
            f'Failed to download GeoTeaser from GIS service: {exc}',
        ) from exc

    return Response(
        content=body,
        media_type=('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        headers={
            'Content-Disposition': (f'attachment; filename="GeoTeaser_{run_id}.xlsx"'),
            'Cache-Control': 'private, no-store',
        },
    )
