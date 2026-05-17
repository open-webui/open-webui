import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlencode
import base64

import httpx

log = logging.getLogger(__name__)


class GitLabFetcher:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            'PRIVATE-TOKEN': token,
            'Content-Type': 'application/json',
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                follow_redirects=True,
                headers=self.headers
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, path: str, params: dict = None, timeout: float = 60.0) -> httpx.Response:
        url = f'{self.url}{path}'
        client = await self.get_client()
        response = await client.get(url, params=params)
        log.debug(f'GET {url} -> {response.status_code}')
        response.raise_for_status()
        return response

    async def test_connection(self) -> Dict[str, Any]:
        resp = await self._get('/api/v4/user')
        return resp.json()

    async def list_projects(self, per_page: int = 100) -> List[Dict[str, Any]]:
        all_projects = []
        page = 1
        while True:
            resp = await self._get('/api/v4/projects', {
                'membership': True,
                'per_page': per_page,
                'page': page,
                'order_by': 'last_activity_at',
                'sort': 'desc',
            })
            projects = resp.json()
            if not projects:
                break
            all_projects.extend(projects)
            if len(projects) < per_page:
                break
            page += 1
        log.info(f'Fetched {len(all_projects)} projects ({page} pages)')
        return all_projects

    async def list_repository_tree(
        self,
        project_id: str,
        ref: str = 'main',
        recursive: bool = True,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        all_items = []
        page = 1
        while True:
            resp = await self._get(
                f'/api/v4/projects/{project_id}/repository/tree',
                {'ref': ref, 'recursive': str(recursive).lower(), 'per_page': per_page, 'page': page},
            )
            items = resp.json()
            if not items:
                break
            all_items.extend(items)
            if len(items) < per_page:
                break
            page += 1
        log.info(f'Fetched {len(all_items)} tree items for project {project_id} (ref={ref}, {page} pages)')
        return all_items

    async def get_file_content(
        self,
        project_id: str,
        file_path: str,
        ref: str = 'main',
    ) -> str:
        encoded = quote(file_path, safe='')
        url = f'/api/v4/projects/{project_id}/repository/files/{encoded}'
        resp = await self._get(url, params={'ref': ref})
        data = resp.json()
        return base64.b64decode(data['content']).decode('utf-8', errors='replace')

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        encoded_id = quote(str(project_id), safe='')
        resp = await self._get(f'/api/v4/projects/{encoded_id}')
        return resp.json()

    async def list_branches(self, project_id: str) -> List[Dict[str, Any]]:
        encoded_id = quote(str(project_id), safe='')
        resp = await self._get(f'/api/v4/projects/{encoded_id}/repository/branches')
        return resp.json()


def create_gitlab_fetcher(url: str, token: str) -> GitLabFetcher:
    return GitLabFetcher(url=url, token=token)
