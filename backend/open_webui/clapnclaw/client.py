import httpx
from open_webui.clapnclaw.config import CLAPNCLAW_API_URL, CLAPNCLAW_WORKSPACE_SECRET


class ClapNClawClient:
    """Async HTTP client for ClapNClaw backend API."""

    def __init__(self):
        self.base_url = CLAPNCLAW_API_URL.rstrip("/")
        self.secret = CLAPNCLAW_WORKSPACE_SECRET

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json_data: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=json_data,
            )
            resp.raise_for_status()
            return resp.json()


clapnclaw_client = ClapNClawClient()
