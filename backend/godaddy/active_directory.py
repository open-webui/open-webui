"""
Active Directory API Client for GoDaddy.

This module provides functions to interact with the GoDaddy Active Directory API
to retrieve user groups when authenticating via OAuth.
"""

import logging
import json
from typing import List, Optional, Dict
import aiohttp
from urllib.parse import urljoin

from godaddy.gd_auth.client import AwsIamAuthTokenClient

# Setup logging
log = logging.getLogger(__name__)

class ActiveDirectoryClient:
    """Client for interacting with the GoDaddy Active Directory API."""
    
    def __init__(
        self, 
        base_url: str,
        sso_host: str,
        refresh_min: float,
        domain: str
    ):
        """
        Initialize the Active Directory client.
        
        Args:
            base_url: The base URL for the Active Directory API
            sso_host: The SSO host for token generation
            refresh_min: How often to refresh SSO Tokens in minutes
            domain: The Active Directory domain to use
        """
        self._base_url = base_url
        self._domain = domain
        self._token_client = AwsIamAuthTokenClient(sso_host=sso_host, refresh_min=refresh_min)
    
    async def get_user_groups(self, user_email: str) -> List[str]:
        """
        Retrieve user groups from the Active Directory API.
        
        Args:
            user_email: Email address of the user
            
        Returns:
            List of group names the user belongs to
        """
        try:
            # Extract username from email (everything before @)
            username = user_email.split('@')[0] if '@' in user_email else user_email
            
            # Get JWT token for authentication
            token = self._token_client.token

            # Prepare headers with JWT
            headers = {
                "Authorization": f"sso-jwt {token}",
                "Content-Type": "application/json"
            }
            
            # Build the API URL using the domain and username
            url = urljoin(self._base_url, f"active_directory/{self._domain}/users/{username}/groups")
            log.debug(f"Making AD API request to: {url}")
            
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        log.debug(f"AD API response: {data}")
                        
                        # Extract group names from the response using the CN attribute
                        groups = []
                        if "data" in data:
                            for group_data in data["data"]:
                                if ("attributes" in group_data and 
                                    "cn" in group_data["attributes"] and 
                                    group_data["attributes"]["cn"]):
                                    
                                    # The CN can be a list, so handle both cases
                                    cn = group_data["attributes"]["cn"]
                                    if isinstance(cn, list):
                                        if cn:  # Make sure the list is not empty
                                            groups.append(cn[0])
                                    else:
                                        groups.append(cn)
                                        
                        log.info(f"Successfully retrieved {len(groups)} groups for user {username} from Active Directory")
                        return groups
                    else:
                        error_text = await response.text()
                        log.error(f"Failed to retrieve user groups: {response.status}, {error_text}")
                        return []
                        
        except Exception as e:
            log.exception(f"Error retrieving user groups from Active Directory API: {e}")
            return []

    async def get_user_details(self, user_email: str) -> Optional[Dict]:
        """
        Retrieve detailed user information from the Active Directory API.
        
        Args:
            user_email: Email address of the user
            
        Returns:
            Dictionary containing user details or None if retrieval fails
        """
        try:
            # Get JWT token for authentication
            token = self._token_client.token
            
            # Prepare headers with JWT
            headers = {
                "Authorization": f"sso-jwt {token}",
                "Content-Type": "application/json"
            }
            
            # Build the API URL
            url = urljoin(self._base_url, f"/api/v1/users/{user_email}")
            
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        log.info(f"Successfully retrieved user details for {user_email}")
                        return data
                    else:
                        error_text = await response.text()
                        log.error(f"Failed to retrieve user details: {response.status}, {error_text}")
                        return None
                        
        except Exception as e:
            log.exception(f"Error retrieving user details from Active Directory API: {e}")
            return None