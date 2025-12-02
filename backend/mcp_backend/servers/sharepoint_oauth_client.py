#!/usr/bin/env python3
"""
SharePoint OAuth2 Client with On-Behalf-Of (OBO) Flow Support

This module handles OAuth2 authentication for SharePoint access, supporting both:
1. Application authentication (client credentials flow)
2. User-delegated authentication (on-behalf-of flow)

The OBO flow allows the MCP server to act on behalf of authenticated users,
respecting their individual SharePoint permissions.
"""
import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger("sharepoint_oauth")


class SharePointOAuthClient:
    """OAuth2 client for SharePoint with On-Behalf-Of flow support"""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        tenant_id: str = None,
        site_url: str = None,
        use_delegated_access: bool = None,
        obo_scope: str = None,
    ):
        """
        Initialize the OAuth client with configuration.

        Args:
            client_id: Azure AD application client ID (if None, uses SHP_ID_APP env var)
            client_secret: Azure AD application client secret (if None, uses SHP_ID_APP_SECRET env var)
            tenant_id: Azure AD tenant ID (if None, uses SHP_TENANT_ID env var)
            site_url: SharePoint site URL (if None, uses SHP_SITE_URL env var)
            use_delegated_access: Enable OBO flow (if None, uses SHP_USE_DELEGATED_ACCESS env var)
            obo_scope: OBO token scopes (if None, uses SHP_OBO_SCOPE env var)
        """
        # Support both direct parameters and environment variables for backward compatibility
        self.client_id = client_id or os.getenv("SHP_ID_APP")
        self.client_secret = client_secret or os.getenv("SHP_ID_APP_SECRET")
        self.tenant_id = tenant_id or os.getenv("SHP_TENANT_ID")
        self.site_url = site_url or os.getenv("SHP_SITE_URL")

        # Global settings with defaults
        if use_delegated_access is not None:
            self.use_delegated_access = use_delegated_access
        else:
            self.use_delegated_access = (
                os.getenv("SHP_USE_DELEGATED_ACCESS", "true").lower() == "true"
                and os.getenv("USER_JWT_TOKEN") is not None
            )

        self.obo_scope = obo_scope or os.getenv(
            "SHP_OBO_SCOPE",
            "https://graph.microsoft.com/Sites.Read.All https://graph.microsoft.com/Files.Read.All",
        )

        if not all([self.client_id, self.client_secret, self.tenant_id, self.site_url]):
            raise ValueError("Missing required SharePoint OAuth configuration")

        # OAuth2 endpoints
        self.token_endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )
        self.graph_base_url = "https://graph.microsoft.com/v1.0"

        logger.info(
            f"Initialized SharePoint OAuth client (delegated: {self.use_delegated_access})"
        )

    async def get_application_token(self) -> Optional[str]:
        """
        Get application-only access token using client credentials flow

        Returns:
            Access token string or None if failed
        """
        try:
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_endpoint, data=token_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        access_token = result.get("access_token")
                        logger.info("Successfully obtained application token")
                        return access_token
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Application token request failed: {response.status} - {error_text}"
                        )
                        return None

        except Exception as e:
            logger.error(f"Error obtaining application token: {e}")
            return None

    async def get_obo_token(self, user_access_token: str) -> Optional[str]:
        """
        Get on-behalf-of access token for SharePoint access

        Args:
            user_access_token: User's access token from CANchat authentication

        Returns:
            OBO access token string or None if failed
        """
        try:
            token_data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "assertion": user_access_token,
                "scope": self.obo_scope,
                "requested_token_use": "on_behalf_of",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_endpoint, data=token_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        access_token = result.get("access_token")
                        logger.info("Successfully obtained OBO token")
                        return access_token
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"OBO token request failed: {response.status} - {error_text}"
                        )
                        return None

        except Exception as e:
            logger.error(f"Error obtaining OBO token: {e}")
            return None

    async def get_access_token(self, user_token: Optional[str] = None) -> Optional[str]:
        """
        Get appropriate access token based on configuration

        Args:
            user_token: Optional user access token for OBO flow

        Returns:
            Access token string or None if failed
        """
        if self.use_delegated_access and user_token:
            logger.info("Using delegated access (OBO flow)")
            return await self.get_obo_token(user_token)
        else:
            logger.info("Using application access (client credentials)")
            return await self.get_application_token()

    def get_site_identifier(self) -> str:
        """
        Extract site identifier from SharePoint URL for Graph API calls

        Returns:
            Site identifier in format: hostname:path
        """
        from urllib.parse import urlparse

        parsed = urlparse(self.site_url)
        hostname = parsed.netloc
        path = parsed.path

        return f"{hostname}:{path}"

    async def make_graph_request(
        self,
        endpoint: str,
        access_token: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Make authenticated request to Microsoft Graph API

        Args:
            endpoint: Graph API endpoint (relative to base URL)
            access_token: Access token for authentication
            method: HTTP method (GET, POST, etc.)
            data: Optional request body data

        Returns:
            Tuple of (success, response_data)
        """
        try:
            url = f"{self.graph_base_url}/{endpoint.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                kwargs = {"headers": headers}
                if data:
                    kwargs["json"] = data

                async with session.request(method, url, **kwargs) as response:
                    if response.status in [200, 201, 204]:
                        try:
                            result = await response.json()
                        except:
                            result = {"status": "success"}
                        logger.debug(
                            f"Graph API request successful: {method} {endpoint}"
                        )
                        return True, result
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Graph API request failed: {response.status} - {error_text}"
                        )
                        return False, {
                            "error": error_text,
                            "status_code": response.status,
                        }

        except Exception as e:
            logger.error(f"Error making Graph API request: {e}")
            return False, {"error": str(e)}

    async def get_site_info(self, access_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get SharePoint site information

        Args:
            access_token: Access token for authentication

        Returns:
            Tuple of (success, site_info)
        """
        site_id = self.get_site_identifier()
        endpoint = f"sites/{site_id}"

        return await self.make_graph_request(endpoint, access_token)

    async def get_site_drives(
        self, access_token: str, site_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get document libraries (drives) for a SharePoint site

        Args:
            access_token: Access token for authentication
            site_id: Optional specific site ID (uses configured site if not provided)

        Returns:
            Tuple of (success, drives_data)
        """
        if not site_id:
            # Get site info first to get site ID
            success, site_info = await self.get_site_info(access_token)
            if not success:
                return False, site_info
            site_id = site_info.get("id")

        if not site_id:
            return False, {"error": "Could not determine site ID"}

        endpoint = f"sites/{site_id}/drives"
        return await self.make_graph_request(endpoint, access_token)

    async def get_drive_items(
        self,
        access_token: str,
        site_id: Optional[str] = None,
        drive_id: Optional[str] = None,
        folder_path: str = "",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get items (files/folders) from a SharePoint drive

        Args:
            access_token: Access token for authentication
            site_id: SharePoint site ID
            drive_id: Drive (document library) ID
            folder_path: Path within the drive (empty for root)

        Returns:
            Tuple of (success, items_data)
        """
        if not site_id or not drive_id:
            # Get default drive
            success, drives_data = await self.get_site_drives(access_token, site_id)
            if not success:
                return False, drives_data

            drives = drives_data.get("value", [])
            if not drives:
                return False, {"error": "No drives found"}

            drive_id = drives[0].get("id")  # Use first drive
            if not site_id:
                site_id = drives[0].get("parentReference", {}).get("siteId")

        if folder_path:
            # Navigate to specific folder
            folder_path_encoded = quote(folder_path, safe="")
            endpoint = f"sites/{site_id}/drives/{drive_id}/root:/{folder_path_encoded}:/children"
        else:
            # Root items
            endpoint = f"sites/{site_id}/drives/{drive_id}/root/children"

        return await self.make_graph_request(endpoint, access_token)

    async def get_file_content(
        self, access_token: str, site_id: str, drive_id: str, file_id: str
    ) -> Tuple[bool, Any]:
        """
        Get content of a specific file by ID

        Args:
            access_token: Access token for authentication
            site_id: SharePoint site ID
            drive_id: Drive ID
            file_id: File ID (not path)

        Returns:
            Tuple of (success, file_content)
        """
        # Use file ID to get content directly
        endpoint = f"sites/{site_id}/drives/{drive_id}/items/{file_id}/content"

        try:
            url = f"{self.graph_base_url}/{endpoint}"
            headers = {"Authorization": f"Bearer {access_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        return True, content
                    else:
                        error_text = await response.text()
                        return False, {
                            "error": error_text,
                            "status_code": response.status,
                        }

        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return False, {"error": str(e)}

    async def test_connection(self, user_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Test the SharePoint connection and permissions

        Args:
            user_token: Optional user token for delegated access

        Returns:
            Dictionary with test results
        """
        result = {
            "oauth_config": "configured",
            "delegated_access": self.use_delegated_access,
            "token_acquisition": "failed",
            "site_access": "failed",
            "drives_access": "failed",
        }

        try:
            # Step 1: Get access token
            access_token = await self.get_access_token(user_token)
            if access_token:
                result["token_acquisition"] = "success"
            else:
                return result

            # Step 2: Test site access
            success, site_info = await self.get_site_info(access_token)
            if success:
                result["site_access"] = "success"
                result["site_info"] = site_info
            else:
                result["site_error"] = site_info
                return result

            # Step 3: Test drives access
            success, drives_data = await self.get_site_drives(access_token)
            if success:
                result["drives_access"] = "success"
                result["drives_count"] = len(drives_data.get("value", []))
                result["drives"] = [d.get("name") for d in drives_data.get("value", [])]
            else:
                result["drives_error"] = drives_data

            return result

        except Exception as e:
            result["test_error"] = str(e)
            return result


# Global OAuth client instance
_oauth_client = None


def get_oauth_client() -> SharePointOAuthClient:
    """Get or create the global OAuth client instance"""
    global _oauth_client
    if _oauth_client is None:
        _oauth_client = SharePointOAuthClient()
    return _oauth_client
