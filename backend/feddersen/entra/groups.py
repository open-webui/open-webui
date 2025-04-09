import asyncio
import logging
import os
import time
from urllib.parse import quote

import aiohttp
from feddersen.util.util import Cache

logger = logging.getLogger(__name__)


class UserGroupsRetriever:
    """
    Helper class to call the MS Graph API as the given service principal in order to retrieve
    the groups, the logged-in user is part of. This resolution is transitive and will return
    a big list usually. In order for this to work, the app registration must have Groups.ReadAll
    permissions on application level.

    Args:
        sso_app_tenant_id (str): The tenant ID for the Azure AD application.
        sso_app_client_id (str): The client ID for the Azure AD application.
        sso_app_client_secret (str): The client secret for the Azure AD application.
        ms_graph_url (str, optional): The Microsoft Graph API URL. Defaults
        to "https://graph.microsoft.com/v1.0".
        cache (Cache, optional): A cache object to store the user groups. Defaults to None.
        cache_duration (int, optional): The duration in seconds for the cache. Defaults to 3600.
        Only relevant when cache is None.

    Raises:
        ValueError: If any of the required Azure AD parameters are not provided.
    """

    def __init__(
        self,
        sso_app_tenant_id: str,
        sso_app_client_id: str,
        sso_app_client_secret: str,
        ms_graph_url: str = "https://graph.microsoft.com/v1.0",
        cache: Cache | None = None,
        cache_duration: int = 3600,
    ):
        if not all([sso_app_tenant_id, sso_app_client_id, sso_app_client_secret]):
            # if all are empty, try to load from env
            sso_app_client_id = os.getenv("MICROSOFT_CLIENT_ID")
            sso_app_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
            sso_app_tenant_id = os.getenv("MICROSOFT_CLIENT_TENANT_ID")

        if not all([sso_app_tenant_id, sso_app_client_id, sso_app_client_secret]):
            raise ValueError("All Azure AD parameters must be provided!")

        self.sso_app_tenant_id = sso_app_tenant_id
        self.sso_app_client_id = sso_app_client_id
        self.sso_app_client_secret = sso_app_client_secret
        self.ms_graph_url = ms_graph_url

        if cache is None:
            self._user_group_cache = Cache(cache_duration=cache_duration)
        else:
            self._user_group_cache = cache

        # Store the access token to avoid retrieving it multiple times
        self._access_token = None
        self._token_expiry = 0

    async def _get_app_token(self) -> str:
        """Get the token to access MS Graph as Webapp asynchronously. This is different to other methods
        here (they carry the signed-in user token)

        Returns:
            str: bearer token
        """
        # Check if we have a valid token already
        current_time = time.time()
        if self._access_token and current_time < self._token_expiry:
            return self._access_token

        # Acquire the Token for the Webapp to call the Graph API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://login.microsoftonline.com/{self.sso_app_tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": self.sso_app_client_id,
                    "scope": "https://graph.microsoft.com/.default",
                    "client_secret": self.sso_app_client_secret,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error("Could not get the token for the app: %s", error_text)
                    resp.raise_for_status()

                try:
                    graph_token = await resp.json()
                except aiohttp.ContentTypeError as e:
                    logger.error("Could not parse token response as JSON")
                    raise e

                # Store the token and its expiry time
                self._access_token = graph_token["access_token"]
                # Set expiry 5 minutes before actual expiry to be safe
                self._token_expiry = (
                    current_time + graph_token.get("expires_in", 3600) - 300
                )

                return self._access_token

    def get_user_groups(
        self, user_mail: str, group_prefix: str = None
    ) -> list[str] | None:
        """
        Retrieve the groups that a user is a transitive member of synchronously.
        This is a wrapper around the async version.

        Args:
            user_mail (str): The user_mail of the user, this is their email address typically.
            group_prefix (str, optional): A prefix filter for the returned user groups.
                                          Defaults to None.

        Returns:
            list[str]: List of group IDs (their display name).
        """

        # Create a new event loop if we're not in one already
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an event loop, we can create a task
                return asyncio.run_coroutine_threadsafe(
                    self.aget_user_groups(user_mail, group_prefix), loop
                ).result()
            else:
                # We have an event loop but it's not running
                return loop.run_until_complete(
                    self.aget_user_groups(user_mail, group_prefix)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.aget_user_groups(user_mail, group_prefix))

    async def aget_user_groups(
        self, user_mail: str, group_prefix: str = None
    ) -> list[str] | None:
        """
        Retrieve the groups that a user is a transitive member of asynchronously.

        Args:
            user_id (str): The user_id of the user, this is their email adress typically.
            group_prefix (str, optional): A prefix filter for the returned user groups.
                                          Defaults to None.

        Returns:
            str: Comma-separated list of group IDs (their display name).
        """
        if not self._user_group_cache[user_mail]:
            token = await self._get_app_token()
            headers = {"Authorization": f"Bearer {token}"}

            user_id = None
            async with aiohttp.ClientSession() as session:
                # First, Fetch the user by principalName. For internals, this is the same as
                # the email address. For externals, it's not (see next try)
                async with session.get(
                    f"{self.ms_graph_url}/users/{quote(user_mail)}",
                    headers=headers,
                    params={"$select": "id"},
                ) as resp:
                    if resp.status == 200:
                        user_data = await resp.json()
                        user_id = user_data.get("id")

                if user_id is None:
                    # The user could not be found by display name. This happens e.g. for external users
                    # Let's find the user's id in the full user list, filtering by email
                    filter = quote(f"mail eq '{user_mail}'")

                    async with session.get(
                        f"{self.ms_graph_url}/users?$filter={filter}",
                        headers=headers,
                        params={"$select": "mail,id"},
                    ) as resp:
                        if resp.status == 200:
                            all_users = await resp.json()
                            if "value" in all_users:
                                for user in all_users["value"]:
                                    if user.get("mail") == user_mail:
                                        user_id = user["id"]
                                        break

                if user_id is None:
                    logger.warning(
                        "Could not find user with email %s in list", user_mail
                    )
                    return []

                # get the groups
                field_to_get = "displayName"
                # MS uses pagination and this is the maximum value possible
                batch_size = 999

                url = f"{self.ms_graph_url}/users/{user_id}/transitiveMemberOf?$select={field_to_get}&$top={batch_size}"
                groups = []

                while url:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error("Error fetching groups: %s", error_text)
                            break

                        response = await resp.json()
                        if "value" in response:
                            groups.extend(response["value"])
                        # None if no more pages
                        url = response.get("@odata.nextLink")

            groups = [g[field_to_get] for g in groups]
            if group_prefix:
                groups = [g for g in groups if g.startswith(group_prefix)]

            self._user_group_cache[user_mail] = groups

        return self._user_group_cache[user_mail]
