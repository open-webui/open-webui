"""
Confluence loader for importing content from Atlassian Confluence Cloud and Data Center.

Supports:
- Confluence Cloud (https://yoursite.atlassian.net)
- Confluence Data Center / Server (https://confluence.yourcompany.com)

Authentication:
- Cloud: email + API token
- Data Center: username + personal access token (PAT), or username + password
"""

import logging
import re
from typing import Iterator, List, Optional
from urllib.parse import urljoin

import requests

log = logging.getLogger(__name__)


class ConfluenceClient:
    """Client for interacting with the Confluence REST API."""

    def __init__(
        self,
        base_url: str,
        auth_type: str = "cloud",  # "cloud" or "datacenter"
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        personal_access_token: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        if auth_type == "cloud":
            if not email or not api_token:
                raise ValueError(
                    "Cloud authentication requires email and api_token"
                )
            self.session.auth = (email, api_token)
        elif auth_type == "datacenter":
            if personal_access_token:
                self.session.headers.update(
                    {"Authorization": f"Bearer {personal_access_token}"}
                )
            elif username and password:
                self.session.auth = (username, password)
            else:
                raise ValueError(
                    "Data Center authentication requires personal_access_token, "
                    "or username and password"
                )
        else:
            raise ValueError(f"Unknown auth_type: {auth_type}")

    def _api_url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = self._api_url(path)
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def test_connection(self) -> dict:
        """Test the connection by fetching server info or current user."""
        try:
            # Try cloud-style current user endpoint first
            return self._get("/wiki/rest/api/user/current")
        except Exception:
            pass
        try:
            # Try data center style
            return self._get("/rest/api/user/current")
        except Exception:
            pass
        # Fallback: try to list spaces (any valid endpoint)
        return self.get_spaces(limit=1)

    def get_spaces(
        self,
        start: int = 0,
        limit: int = 25,
        space_type: Optional[str] = None,
    ) -> dict:
        """Get all spaces the authenticated user has access to."""
        params = {"start": start, "limit": limit, "expand": "description.plain"}
        if space_type:
            params["type"] = space_type

        # Try wiki-prefixed URL first (Cloud), then plain (Data Center)
        for prefix in ["/wiki/rest/api/space", "/rest/api/space"]:
            try:
                return self._get(prefix, params)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
            except requests.exceptions.JSONDecodeError:
                continue
        raise Exception("Could not reach Confluence space API. Please check your provided Base URL.")

    def get_all_spaces(self, space_type: Optional[str] = None) -> List[dict]:
        """Fetch all spaces handling pagination."""
        all_spaces = []
        start = 0
        limit = 25
        while True:
            result = self.get_spaces(start=start, limit=limit, space_type=space_type)
            spaces = result.get("results", [])
            all_spaces.extend(spaces)
            if len(spaces) < limit:
                break
            start += limit
        return all_spaces

    def get_personal_space(self) -> List[dict]:
        """Fetch the authenticated user's personal space."""
        try:
            # 1. Get current user's profile to extract accountId or username
            user_info = self._get("/rest/api/user/current")
            
            # Confluence Cloud uses accountId, Server/Data Center might use username
            user_id = user_info.get("accountId") or user_info.get("username")
            if not user_id:
                raise Exception("Could not determine user ID for personal space.")
                
            space_key = f"~{user_id}"
            
            # 2. Fetch just this specific space
            for prefix in ["/wiki/rest/api/space", "/rest/api/space"]:
                try:
                    space = self._get(f"{prefix}/{space_key}", {"expand": "description.plain"})
                    return [space]
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 404:
                        continue
                    raise
                except requests.exceptions.JSONDecodeError:
                    continue
        except Exception as e:
            # If the personal space doesn't exist or isn't accessible, return empty list
            return []
            
        return []

    def get_space_content(
        self,
        space_key: str,
        start: int = 0,
        limit: int = 25,
        content_type: str = "page",
        expand: str = "body.storage,metadata.labels,version,ancestors",
    ) -> dict:
        """Get content from a specific space."""
        params = {
            "spaceKey": space_key,
            "type": content_type,
            "start": start,
            "limit": limit,
            "expand": expand,
        }
        for prefix in ["/wiki/rest/api/content", "/rest/api/content"]:
            try:
                return self._get(prefix, params)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
            except requests.exceptions.JSONDecodeError:
                continue
        raise Exception("Could not reach Confluence content API. Please check your provided Base URL.")

    def get_all_space_content(
        self,
        space_key: str,
        content_type: str = "page",
    ) -> List[dict]:
        """Get all content from a space using pagination."""
        all_content = []
        start = 0
        limit = 25
        while True:
            result = self.get_space_content(
                space_key=space_key,
                start=start,
                limit=limit,
                content_type=content_type,
            )
            content = result.get("results", [])
            all_content.extend(content)
            if len(content) < limit:
                break
            start += limit
        return all_content

    def get_page_by_id(
        self,
        page_id: str,
        expand: str = "body.storage,metadata.labels,version",
    ) -> dict:
        """Get a specific page by ID."""
        params = {"expand": expand}
        for prefix in [
            f"/wiki/rest/api/content/{page_id}",
            f"/rest/api/content/{page_id}",
        ]:
            try:
                return self._get(prefix, params)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
            except requests.exceptions.JSONDecodeError:
                continue
        raise Exception(f"Could not fetch page {page_id}. Please check your provided Base URL.")


def html_to_text(html_content: str) -> str:
    """Convert Confluence storage format HTML to plain text.

    Strips HTML tags and normalizes whitespace. This handles Confluence's
    XHTML storage format which includes macros, structured macros, etc.
    """
    if not html_content:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()

        # Remove Confluence macros that don't contribute text content
        for macro in soup.find_all("ac:structured-macro"):
            macro_name = macro.get("ac:name", "")
            # Keep text-producing macros, remove UI-only ones
            if macro_name in [
                "toc",
                "toc-zone",
                "children",
                "page-tree",
                "livesearch",
                "recently-updated",
                "space-details",
            ]:
                macro.decompose()

        # Get text with reasonable spacing
        text = soup.get_text(separator="\n")
    except ImportError:
        # Fallback: use regex to strip HTML tags
        text = re.sub(r"<[^>]+>", "\n", html_content)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def confluence_page_to_document(page: dict, space_key: str = "") -> dict:
    """Convert a Confluence page dict to a document-like dict with page_content and metadata."""
    title = page.get("title", "Untitled")

    # Extract body content
    body = page.get("body", {})
    storage = body.get("storage", {})
    html_content = storage.get("value", "")

    text_content = html_to_text(html_content)

    # Build content with title as header
    page_content = f"# {title}\n\n{text_content}" if text_content else f"# {title}"

    # Extract metadata
    version = page.get("version", {})
    labels = page.get("metadata", {}).get("labels", {}).get("results", [])
    label_names = [l.get("name", "") for l in labels]

    metadata = {
        "source": "confluence",
        "space_key": space_key,
        "page_id": str(page.get("id", "")),
        "title": title,
        "version": version.get("number", 1),
        "last_modified_by": version.get("by", {}).get("displayName", ""),
        "labels": ", ".join(label_names),
    }

    # Add URL if available
    links = page.get("_links", {})
    if "webui" in links:
        base = links.get("base", "")
        metadata["url"] = base + links["webui"] if base else links["webui"]

    return {
        "page_content": page_content,
        "metadata": metadata,
    }
