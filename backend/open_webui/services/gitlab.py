from typing import Optional, List, Dict, Any
import logging
from urllib.parse import urlparse, quote

import httpx

log = logging.getLogger(__name__)


class GitLabClient:
    def __init__(self, url: str, token: str):
        # Handle cases where user provides full repo URL instead of base URL
        parsed = urlparse(url.rstrip('/'))
        
        # If it looks like a gitlab repo URL (e.g. gitlab.com/owner/repo)
        # we want to extract just the base URL.
        path_parts = [p for p in parsed.path.split('/') if p]
        
        base_path = ""
        # If the instance is at a subpath (e.g. company.com/gitlab), we need to keep that
        # but if it's a repo path (e.g. gitlab.com/owner/repo), we discard owner/repo.
        # This is tricky, but we can assume that if there are more than 2 parts, 
        # it's likely owner/repo/..., unless it's /api/v4.
        
        filtered_parts = []
        for part in path_parts:
            if part == 'api': break
            filtered_parts.append(part)
        
        # If we have owner/repo, path_parts will have >= 2 parts.
        # Most GitLab instances are at the root or a single subpath.
        if len(filtered_parts) > 1 and parsed.netloc == 'gitlab.com':
            # For gitlab.com, any path is owner/repo
            self.url = f"{parsed.scheme}://{parsed.netloc}"
        elif len(filtered_parts) > 2:
            # For self-hosted, more than 2 parts is likely owner/repo
            self.url = f"{parsed.scheme}://{parsed.netloc}/{filtered_parts[0]}"
        else:
            self.url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if self.url.endswith('/api/v4'):
                self.url = self.url[:-7]
        
        self.url = self.url.rstrip('/')
        self.token = token
        self.headers = {
            'PRIVATE-TOKEN': token,
            'Content-Type': 'application/json',
        }

    def _get_client(self, timeout: float = 30.0):
        return httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def test_connection(self) -> Dict[str, Any]:
        async with self._get_client() as client:
            response = await client.get(
                f'{self.url}/api/v4/user',
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_projects(self, per_page: int = 20, page: int = 1, search: str = '') -> List[Dict[str, Any]]:
        """List projects the authenticated user has access to."""
        params = {
            'membership': True,
            'per_page': per_page,
            'page': page,
            'order_by': 'last_activity_at',
            'sort': 'desc',
        }
        if search:
            params['search'] = search

        async with self._get_client() as client:
            response = await client.get(
                f'{self.url}/api/v4/projects',
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_all_user_projects(self) -> List[Dict[str, Any]]:
        """Fetch all accessible projects across all pages."""
        all_projects = []
        page = 1
        while True:
            projects = await self.list_projects(per_page=100, page=page)
            if not projects:
                break
            all_projects.extend(projects)
            if len(projects) < 100:
                break
            page += 1
        return all_projects

    async def list_repository_tree(
        self,
        project_id: str,
        ref: str = 'main',
        recursive: bool = True,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        async with self._get_client(timeout=60.0) as client:
            response = await client.get(
                f'{self.url}/api/v4/projects/{project_id}/repository/tree',
                params={
                    'ref': ref,
                    'recursive': recursive,
                    'per_page': per_page,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_file_content(
        self,
        project_id: str,
        file_path: str,
        ref: str = 'main',
    ) -> str:
        async with self._get_client(timeout=60.0) as client:
            response = await client.get(
                f'{self.url}/api/v4/projects/{project_id}/repository/files/{file_path}',
                params={'ref': ref},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            import base64
            return base64.b64decode(data['content']).decode('utf-8', errors='replace')

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        async with self._get_client() as client:
            encoded_id = quote(project_id, safe='')
            response = await client.get(
                f'{self.url}/api/v4/projects/{encoded_id}',
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_branches(self, project_id: str) -> List[Dict[str, Any]]:
        async with self._get_client() as client:
            encoded_id = quote(project_id, safe='')
            response = await client.get(
                f'{self.url}/api/v4/projects/{encoded_id}/repository/branches',
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()


def create_gitlab_client(url: str, token: str) -> GitLabClient:
    return GitLabClient(url=url, token=token)