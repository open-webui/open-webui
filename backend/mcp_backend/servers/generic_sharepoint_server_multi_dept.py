#!/usr/bin/env python3
"""
Multi-Department Generic SharePoint MCP Server with On-Behalf-Of (OBO) Flow Support

This server provides SharePoint document search and retrieval capabilities
for multiple departments/organizations using Microsoft Graph API with OBO flow for user-scoped access.

This is a generic, reusable implementation that can be instantiated for any department
by providing a department prefix (e.g., MPO, FIN, IT) to access department-specific environment variables.

Global environment variables (shared across all departments):
- SHP_USE_DELEGATED_ACCESS: Enable user-scoped access (true/false, default: true)
- SHP_OBO_SCOPE: Scopes for On-Behalf-Of token exchange (default: standard Graph scopes)
- SHP_GLOBAL_SEARCH_LIMIT: Maximum total results across all folders before terminating search (default: 30)
- SHP_FOLDER_SEARCH_LIMIT: Maximum number of discovered folders to search (default: 5)

Department-specific environment variables (prefix with DEPT_):
- {DEPT}_SHP_ID_APP: Azure App Registration Client ID
- {DEPT}_SHP_ID_APP_SECRET: Azure App Registration Client Secret
- {DEPT}_SHP_TENANT_ID: Azure AD Tenant ID
- {DEPT}_SHP_SITE_URL: SharePoint Site URL
- {DEPT}_SHP_ORG_NAME: Organization name for tool descriptions
- {DEPT}_SHP_DOC_LIBRARY: SharePoint Document Library path (optional)
- {DEPT}_SHP_DEFAULT_SEARCH_FOLDERS: Comma-separated list of default folders to search in

Example usage:
- For MPO: create server with department_prefix="MPO"
- For Finance: create server with department_prefix="FIN"
- For IT: create server with department_prefix="IT"
"""

import os
import sys
import asyncio
import json
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    try:
        from .sharepoint_oauth_client import SharePointOAuthClient
    except ImportError:
        from sharepoint_oauth_client import (
            SharePointOAuthClient,
        )  # noqa: DEP001 - local module, standalone script fallback
    from fastmcp import FastMCP

    mcp = FastMCP("Generic SharePoint Server - Multi-Department")

    # Global MCP server instance (will be configured per department)
    generic_sharepoint_server = mcp

except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    raise


# Authentication error message for delegated access mode
DELEGATED_ACCESS_AUTH_ERROR = (
    "DELEGATED ACCESS MODE: User authentication token is required but not provided. "
    "SharePoint access with user permissions requires a valid OAuth2 access token. "
    "This request cannot proceed without proper authentication. "
    "Either provide a valid user token or set SHP_USE_DELEGATED_ACCESS=false to use application access."
)


def clean_env_var(value: str) -> str:
    """Clean environment variable by removing quotes and inline comments"""
    if not value:
        return value
    # Remove quotes and inline comments
    value = value.strip("\"'")
    value = re.sub(r"\s*#.*$", "", value)
    value = value.strip("\"'").strip()
    return value


class DepartmentSharePointConfig:
    """Configuration class for department-specific SharePoint settings"""

    def __init__(self, department_prefix: str):
        self.department_prefix = department_prefix.upper()

        # Global settings (shared across all departments)
        # Delegated access setting - can be overridden via environment variable
        self.use_delegated_access = clean_env_var(
            os.getenv("SHP_USE_DELEGATED_ACCESS", "true")
        ).lower() in (
            "true",
            "1",
            "yes",
        )  # Read from environment, default true
        self.obo_scope = clean_env_var(
            os.getenv(
                "SHP_OBO_SCOPE",
                "https://graph.microsoft.com/Sites.Read.All https://graph.microsoft.com/Files.Read.All",
            )
        )

        # Performance settings - configurable via environment variables
        self.global_search_limit = int(
            clean_env_var(os.getenv("SHP_GLOBAL_SEARCH_LIMIT", "20"))  # Reduced from 30
        )
        self.folder_search_limit = int(
            clean_env_var(os.getenv("SHP_FOLDER_SEARCH_LIMIT", "3"))  # Reduced from 5
        )

        # Department-specific settings
        self.site_url = clean_env_var(
            os.getenv(f"{self.department_prefix}_SHP_SITE_URL", "")
        )
        self.org_name = clean_env_var(
            os.getenv(
                f"{self.department_prefix}_SHP_ORG_NAME",
                f"{department_prefix} Department",
            )
        )
        self.doc_library = clean_env_var(
            os.getenv(f"{self.department_prefix}_SHP_DOC_LIBRARY", "")
        )
        self.default_search_folders = (
            os.getenv(f"{self.department_prefix}_SHP_DEFAULT_SEARCH_FOLDERS", "").split(
                ","
            )
            if os.getenv(f"{self.department_prefix}_SHP_DEFAULT_SEARCH_FOLDERS")
            else []
        )

        # Clean up empty strings and comments in search folders
        self.default_search_folders = [
            clean_env_var(folder)
            for folder in self.default_search_folders
            if clean_env_var(folder)
        ]

        # Validation
        self.validate_config()

    def validate_config(self):
        """Validate that required configuration is present"""
        # Only site URL is required for delegated access mode
        if not self.site_url:
            raise ValueError(
                f"Missing required environment variable: {self.department_prefix}_SHP_SITE_URL"
            )


# Global variables (will be set when server is initialized)
config: Optional[DepartmentSharePointConfig] = None
oauth_client: Optional[SharePointOAuthClient] = None
logger = logging.getLogger(__name__)


def initialize_department_server(department_prefix: str):
    """Initialize the server for a specific department"""
    global config, oauth_client

    try:
        # Load department-specific configuration
        config = DepartmentSharePointConfig(department_prefix)

        # Initialize OAuth client with department-specific credentials
        oauth_client = SharePointOAuthClient(
            client_id=os.getenv(f"{department_prefix}_SHP_ID_APP"),
            client_secret=os.getenv(f"{department_prefix}_SHP_ID_APP_SECRET"),
            tenant_id=os.getenv(f"{department_prefix}_SHP_TENANT_ID"),
            site_url=config.site_url,
            use_delegated_access=config.use_delegated_access,
            obo_scope=config.obo_scope,
        )

        logger.info(f"Initialized SharePoint server for department: {config.org_name}")
        logger.info(
            f"Configuration: delegated_access={config.use_delegated_access}, site_url={config.site_url}"
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to initialize SharePoint server for {department_prefix}: {e}"
        )
        # Return False to allow other MCP servers to continue
        return False


def extract_user_token(context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Extract the user's OAuth token from context or environment"""
    # First try context (passed from crew MCP manager)
    if context and "user_token" in context:
        return context["user_token"]

    # Fallback to environment variable
    user_token = os.getenv("USER_JWT_TOKEN")
    if user_token and user_token != "user_token_placeholder":
        return user_token

    return None


async def _get_sharepoint_document_content_impl(
    folder_name: str, file_name: str, user_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve the content of a specific SharePoint document using Microsoft Graph API.

    Args:
        folder_name: SharePoint folder containing the document
        file_name: Name of the document file
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with document content and metadata
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized with department configuration",
            "message": "Please initialize server with a valid department prefix",
        }

    try:
        # Get user token from environment variable if not provided
        if not user_token:
            user_token = os.getenv("USER_JWT_TOKEN")

        # For local development, don't try OBO if no valid token available
        if user_token == "user_token_placeholder" or not user_token:
            user_token = None

        # STRICT AUTHENTICATION CHECK: If delegated access is enabled, user token is REQUIRED
        if config.use_delegated_access:
            if not user_token or not user_token.strip():
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "folder": folder_name,
                    "file": file_name,
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }
        # No verbose logging during parallel processing

        # Silent document content retrieval
        # Get appropriate access token based on configuration
        if config.use_delegated_access:
            access_token = await oauth_client.get_access_token(user_token)
        else:
            access_token = await oauth_client.get_application_token()
        if not access_token:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": "Failed to obtain access token",
                "message": f"Authentication failed for {config.org_name} SharePoint. Please ensure you have the necessary permissions to access this file.",
                "organization": config.org_name,
            }

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": site_info,
                "message": "Failed to access SharePoint site",
                "organization": config.org_name,
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": drives_data,
                "message": "Failed to access document libraries",
                "organization": config.org_name,
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": "No document libraries found",
                "message": "No accessible document libraries found",
                "organization": config.org_name,
            }

        drive_id = drives[0].get("id")

        # Find the specific document
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_name
        )
        if not success:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": items_data,
                "message": f"Failed to access folder: {folder_name}",
                "organization": config.org_name,
            }

        items = items_data.get("value", [])
        target_file = None

        for item in items:
            if item.get("name") == file_name and item.get("file"):
                target_file = item
                break

        if not target_file:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": "File not found",
                "message": f"Document '{file_name}' not found in folder '{folder_name}'",
                "organization": config.org_name,
            }

        # Download the file content
        file_id = target_file.get("id")
        success, file_content = await oauth_client.get_file_content(
            access_token, site_id, drive_id, file_id
        )

        if not success:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": file_content,
                "message": "Failed to download file content",
                "organization": config.org_name,
            }

        # Parse the document content using embedded parser
        try:
            # Suppress any parsing logs
            import logging

            dept_logger = logging.getLogger(f"{config.department_prefix}-SharePoint")
            original_level = dept_logger.level
            dept_logger.setLevel(logging.ERROR)  # Suppress extraction logs

            try:
                parsed_content = await parse_document_content_embedded(
                    file_content, file_name
                )
            finally:
                dept_logger.setLevel(original_level)  # Restore log level

            return {
                "status": "success",
                "folder": folder_name,
                "file": file_name,
                "content": parsed_content,
                "size": target_file.get("size"),
                "lastModified": target_file.get("lastModifiedDateTime"),
                "webUrl": target_file.get("webUrl"),
                "organization": config.org_name,
                "authentication": "Microsoft Graph API with On-Behalf-Of flow",
                "message": f"Successfully extracted content from {file_name} in {config.org_name}",
            }

        except Exception as parse_error:
            logger.error(f"Error parsing document {file_name}: {parse_error}")
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": str(parse_error),
                "message": f"Failed to parse document content: {parse_error}",
                "organization": config.org_name,
            }

    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        return {
            "status": "error",
            "folder": folder_name,
            "file": file_name,
            "error": str(e),
            "message": f"Failed to retrieve {config.org_name} document content",
            "organization": config.org_name,
        }


async def _get_all_documents_comprehensive_impl(
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get ALL documents from SharePoint by traversing every single folder.
    This bypasses the broken search API and actually finds everything.
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized",
            "message": "Server not initialized with department configuration",
        }

    try:
        # Silent comprehensive folder traversal
        # Get authentication token - check environment variable if not provided
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # STRICT AUTHENTICATION CHECK: If delegated access is enabled, user token is REQUIRED
        if config.use_delegated_access:
            if (
                not effective_token
                or effective_token == "user_token_placeholder"
                or not effective_token.strip()
            ):
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }

        if config.use_delegated_access:
            access_token = await oauth_client.get_access_token(effective_token)
        else:
            access_token = await oauth_client.get_application_token()

        if not access_token:
            return {"status": "error", "message": "Failed to get access token"}

        # Get site and drives
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to get site info: {site_info}",
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to get drives: {drives_data}",
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {"status": "error", "message": "No drives found"}

        drive_id = drives[0].get("id")

        # Recursively get documents - limit to default_search_folders if configured
        all_documents = []
        folders_processed = {"count": 0}  # Track folder count

        # If default_search_folders is configured, only search those specific folders
        if config.default_search_folders:
            logger.info(f"Searching specific folders: {config.default_search_folders}")
            for folder_path in config.default_search_folders:
                await _traverse_all_folders_recursive(
                    oauth_client,
                    access_token,
                    site_id,
                    drive_id,
                    folder_path,
                    all_documents,
                    folders_processed,
                    max_depth=10,
                )
            search_scope = f"folders: {', '.join(config.default_search_folders)}"
        else:
            # No specific folders configured - search everything from root
            await _traverse_all_folders_recursive(
                oauth_client,
                access_token,
                site_id,
                drive_id,
                "",
                all_documents,
                folders_processed,
                max_depth=10,
            )
            search_scope = "all folders (no default_search_folders configured)"

        return {
            "status": "success",
            "total_documents": len(all_documents),
            "folders_processed": folders_processed["count"],
            "documents": all_documents,
            "organization": config.org_name,
            "search_scope": search_scope,
            "message": f"Found {len(all_documents)} documents from {folders_processed['count']} folders in {search_scope}",
        }

    except Exception as e:
        logger.error(f"Error in comprehensive document retrieval: {e}")
        return {
            "status": "error",
            "message": f"Failed to get all documents: {str(e)}",
            "organization": config.org_name,
        }


async def _traverse_all_folders_recursive(
    oauth_client,
    access_token: str,
    site_id: str,
    drive_id: str,
    folder_path: str,
    all_documents: list,
    folders_processed: dict,
    max_depth: int = 10,
    current_depth: int = 0,
):
    """Recursively traverse ALL folders and collect ALL documents"""
    if current_depth >= max_depth:
        return

    try:
        folders_processed["count"] += 1  # Increment folder count

        # Get all items in current folder
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_path
        )

        if not success:
            logger.warning(f"Failed to access folder: {folder_path}")
            return

        items = items_data.get("value", [])

        for item in items:
            if item.get("file"):  # It's a file
                doc_info = {
                    "name": item.get("name", "Unknown"),
                    "id": item.get("id", ""),
                    "webUrl": item.get("webUrl", ""),
                    "lastModified": item.get("lastModifiedDateTime", ""),
                    "size": item.get("size", 0),
                    "folder_path": folder_path,
                    "organization": config.org_name,
                }
                all_documents.append(doc_info)

            elif item.get("folder"):  # It's a folder, recurse into it
                subfolder_name = item.get("name", "")
                if subfolder_name:
                    subfolder_path = (
                        f"{folder_path}/{subfolder_name}"
                        if folder_path
                        else subfolder_name
                    )
                    await _traverse_all_folders_recursive(
                        oauth_client,
                        access_token,
                        site_id,
                        drive_id,
                        subfolder_path,
                        all_documents,
                        folders_processed,
                        max_depth,
                        current_depth + 1,
                    )

    except Exception as e:
        logger.warning(f"Error traversing folder {folder_path}: {e}")


async def _list_folder_contents_impl(
    folder_path: str,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all files and folders in a specific SharePoint folder path.
    Use this when you need to list/count files in a specific folder, not search for content.

    Args:
        folder_path: Path to the folder (e.g., "Canchat Demo", "Documents/Reports", "" for root)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with list of files and folders

    Example:
        - List files in "Canchat Demo" folder: folder_path="Canchat Demo"
        - List root folder: folder_path=""
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized",
            "message": "Server not initialized with department configuration",
        }

    try:
        import time

        start_time = time.time()

        # Get authentication token
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # STRICT AUTHENTICATION CHECK
        if config.use_delegated_access:
            if (
                not effective_token
                or effective_token == "user_token_placeholder"
                or not effective_token.strip()
            ):
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }

        # Get access token
        if config.use_delegated_access:
            access_token = await oauth_client.get_access_token(effective_token)
        else:
            access_token = await oauth_client.get_application_token()

        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token",
                "organization": config.org_name,
            }

        # Get site info
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to get site info: {site_info}",
                "organization": config.org_name,
            }

        site_id = site_info.get("id")

        # Get drives for the site
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to get drives: {drives_data}",
                "organization": config.org_name,
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "message": "No document libraries found",
                "organization": config.org_name,
            }

        drive_id = drives[0].get("id")  # Use the first/default drive

        # Get items in the folder
        success, items_data = await oauth_client.get_drive_items(
            access_token=access_token,
            site_id=site_id,
            drive_id=drive_id,
            folder_path=folder_path,
        )

        if not success:
            error_msg = items_data.get("error", "Unknown error")

            # If folder not found and we have a folder name, try searching for it GLOBALLY (not limited to this site)
            if "itemNotFound" in str(error_msg) and folder_path:
                logger.info(
                    f"Folder '{folder_path}' not found at direct path in configured site, searching globally..."
                )

                # Use search API to find the folder ACROSS ALL SHAREPOINT (don't limit by site_id)
                # This allows finding folders in personal OneDrive or other team sites
                search_success, search_results = await oauth_client.search_documents(
                    access_token=access_token,
                    query=f'"{folder_path}"',  # Simple query for folder name
                    site_id=None,  # Don't limit to specific site - search everywhere user has access
                    limit=10,
                )

                if search_success and search_results.get("hits"):
                    hits = search_results.get("hits", [])
                    folder_found = False

                    # Look for exact folder name match
                    for hit in hits:
                        resource = hit.get("resource", {})
                        resource_name = resource.get("name", "")

                        # Check if this is a folder - either has "folder" property OR size is 0
                        is_folder = "folder" in resource or (
                            resource.get("size", -1) == 0
                            and "/" in resource.get("webUrl", "")
                        )

                        if is_folder and resource_name.lower() == folder_path.lower():
                            # Found the folder! Now get its items using the ID
                            folder_id = resource.get("id")
                            parent_ref = resource.get("parentReference", {})
                            folder_drive_id = parent_ref.get("driveId")
                            folder_site_id = parent_ref.get("siteId")

                            if not folder_drive_id:
                                logger.warning(
                                    f"Found folder '{folder_path}' but no drive ID available"
                                )
                                continue

                            logger.info(
                                f"Found folder '{folder_path}' via global search (is_folder check passed), retrieving contents..."
                            )

                            # Get items using the folder's ID directly
                            endpoint = (
                                f"drives/{folder_drive_id}/items/{folder_id}/children"
                            )
                            success, items_data = await oauth_client.make_graph_request(
                                endpoint, access_token
                            )

                            if success:
                                folder_found = True
                                logger.info(
                                    f"Successfully retrieved contents of folder '{folder_path}' from global search"
                                )
                                break
                            else:
                                logger.warning(
                                    "Found folder but failed to retrieve contents"
                                )

                    if not folder_found:
                        # Provide helpful error message with what we did find
                        folder_candidates = []
                        for hit in hits:
                            resource = hit.get("resource", {})
                            is_folder = "folder" in resource or (
                                resource.get("size", -1) == 0
                                and "/" in resource.get("webUrl", "")
                            )
                            if is_folder:
                                folder_candidates.append(resource.get("name", ""))

                        return {
                            "status": "error",
                            "message": f"Folder '{folder_path}' not found. Searched all accessible SharePoint sites and OneDrive locations. Similar folders found: {', '.join(folder_candidates[:5]) if folder_candidates else 'none'}",
                            "folder_path": folder_path,
                            "organization": config.org_name,
                            "hint": "The folder might be in a different SharePoint site or personal OneDrive. Try using the search tool instead to find documents by content.",
                        }
                else:
                    return {
                        "status": "error",
                        "message": f"Folder '{folder_path}' not found in configured SharePoint site '{config.site_url}' or any other accessible location. The folder may not exist or you may not have permission to access it.",
                        "folder_path": folder_path,
                        "organization": config.org_name,
                        "hint": "Try using the search tool to find documents by content instead of folder name.",
                    }

            # If still not successful, return error
            if not success:
                return {
                    "status": "error",
                    "message": f"Failed to list folder contents: {error_msg}",
                    "folder_path": folder_path,
                    "organization": config.org_name,
                }

        # Process items into a clean format
        items = items_data.get("value", [])
        files = []
        folders = []

        for item in items:
            item_info = {
                "name": item.get("name", "Unknown"),
                "id": item.get("id", ""),
                "webUrl": item.get("webUrl", ""),
                "lastModified": item.get("lastModifiedDateTime", ""),
                "created": item.get("createdDateTime", ""),
            }

            # Check if it's a folder or file
            if "folder" in item:
                item_info["type"] = "folder"
                item_info["childCount"] = item.get("folder", {}).get("childCount", 0)
                folders.append(item_info)
            else:
                item_info["type"] = "file"
                item_info["size"] = item.get("size", 0)
                item_info["mimeType"] = item.get("file", {}).get("mimeType", "")
                files.append(item_info)

        # Calculate performance
        end_time = time.time()
        processing_time = end_time - start_time

        logger.info(
            f"📁 Listed folder '{folder_path}': {len(files)} files, {len(folders)} folders in {round(processing_time, 2)}s"
        )

        return {
            "status": "success",
            "folder_path": folder_path,
            "total_files": len(files),
            "total_folders": len(folders),
            "files": files,
            "folders": folders,
            "organization": config.org_name,
            "processing_time_seconds": round(processing_time, 2),
            "message": f"✅ Found {len(files)} files and {len(folders)} folders in '{folder_path}'",
        }

    except Exception as e:
        logger.error(f"Error listing folder contents: {e}")
        return {
            "status": "error",
            "message": f"Failed to list folder: {str(e)}",
            "folder_path": folder_path,
            "organization": config.org_name,
        }


async def _search_documents_fast_impl(
    query: str,
    limit: int = 25,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    FAST document search using Microsoft Graph Search API with KQL support.
    This is the NEW recommended method - sub-1 second vs 20-60 seconds with folder traversal.

    Results are sorted by relevance score (most relevant first).

    Args:
        query: Search query (supports plain text or KQL syntax)
        limit: Maximum number of results (default 25, max 500)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with search results

    Example queries:
        - Plain text: "railway infrastructure projects"
        - KQL filename filter: "filename:*.pdf AND railway"
        - KQL date filter: "lastModifiedTime>=2024-01-01 AND infrastructure"
        - Complex KQL: "(railway OR infrastructure OR transportation) AND filename:*.pdf"
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized",
            "message": "Server not initialized with department configuration",
        }

    try:
        import time

        start_time = time.time()

        # Get authentication token
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # STRICT AUTHENTICATION CHECK
        if config.use_delegated_access:
            if (
                not effective_token
                or effective_token == "user_token_placeholder"
                or not effective_token.strip()
            ):
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }

        # Get access token
        if config.use_delegated_access:
            access_token = await oauth_client.get_access_token(effective_token)
        else:
            access_token = await oauth_client.get_application_token()

        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token",
                "organization": config.org_name,
            }

        # Get site ID for scoped search
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to get site info: {site_info}",
                "organization": config.org_name,
            }

        site_id = site_info.get("id")

        # Call the new search API
        success, search_results = await oauth_client.search_documents(
            access_token=access_token,
            query=query,
            site_id=site_id,
            limit=limit,
        )

        if not success:
            # Distinguish between transient API failures, permission errors, and other errors
            is_transient = search_results.get("transient", False)
            is_permission_error = search_results.get("is_permission_error", False)
            status_code = search_results.get("status_code", 0)
            error_msg = search_results.get("error", "Unknown error")

            if is_permission_error:
                # Permission/authorization error - user doesn't have access
                return {
                    "status": "error",
                    "message": f"🔒 Access Denied: You do not have permission to access the requested SharePoint documents. This may be because the documents are in a restricted site, folder, or require additional permissions. Please contact your SharePoint administrator if you believe you should have access.",
                    "organization": config.org_name,
                    "is_permission_error": True,
                    "status_code": status_code,
                }
            elif is_transient:
                # Transient failure - Microsoft's API is temporarily down
                return {
                    "status": "error",
                    "message": f"⚠️ Search temporarily unavailable: {error_msg}",
                    "organization": config.org_name,
                    "transient": True,
                    "retry_suggested": True,
                }
            else:
                # Permanent error (invalid query, etc.)
                return {
                    "status": "error",
                    "message": f"Search failed: {error_msg}",
                    "organization": config.org_name,
                    "transient": False,
                }

        # Process search hits into a clean format
        hits = search_results.get("hits", [])
        documents = []

        for hit in hits:
            resource = hit.get("resource", {})
            web_url = resource.get("webUrl", "")

            # Extract document metadata
            doc_info = {
                "name": resource.get("name", "Unknown"),
                "id": resource.get("id", ""),
                "webUrl": web_url,
                "lastModified": resource.get("lastModifiedDateTime", ""),
                "size": resource.get("size", 0),
                "created": resource.get("createdDateTime", ""),
                "organization": config.org_name,
            }

            # Check if this is a folder (preserve folder metadata)
            # Folders can be identified by:
            # 1. Having a "folder" property in the resource
            # 2. Having size == 0 AND no file extension in webUrl
            has_folder_property = "folder" in resource
            size = resource.get("size", 0)
            has_file_extension = (
                "." in resource.get("name", "").split("/")[-1]
                if resource.get("name")
                else False
            )

            if has_folder_property or (size == 0 and not has_file_extension):
                doc_info["is_folder"] = True
                if has_folder_property:
                    doc_info["folder_child_count"] = resource.get("folder", {}).get(
                        "childCount", 0
                    )
            else:
                doc_info["is_folder"] = False

            # Extract folder path if available
            parent_ref = resource.get("parentReference", {})
            if "path" in parent_ref:
                # Path format: /drives/{drive-id}/root:/path/to/folder
                path_parts = parent_ref.get("path", "").split("/root:")
                if len(path_parts) > 1:
                    doc_info["folder_path"] = path_parts[1].strip("/")
                else:
                    doc_info["folder_path"] = ""
            else:
                doc_info["folder_path"] = ""

            # Store parent reference info for folder operations
            if parent_ref:
                doc_info["driveId"] = parent_ref.get("driveId")
                doc_info["siteId"] = parent_ref.get("siteId")

            # Add hit rank/relevance if available
            if "rank" in hit:
                doc_info["search_rank"] = hit["rank"]

            # Add summary/snippet if available
            if "summary" in hit:
                doc_info["summary"] = hit["summary"]

            documents.append(doc_info)

        # Calculate performance
        end_time = time.time()
        processing_time = end_time - start_time

        # Performance logging
        perf_message = f"⚡ FAST SEARCH: '{query}' → {len(documents)} results in {round(processing_time, 2)}s"
        logger.info(perf_message)
        return {
            "status": "success",
            "query": query,
            "total_results": len(documents),
            "documents": documents,
            "organization": config.org_name,
            "processing_time_seconds": round(processing_time, 2),
            "method": "Microsoft Graph Search API (Fast)",
            "message": f"⚡ Found {len(documents)} documents in {round(processing_time, 2)}s using fast search",
        }

    except Exception as e:
        logger.error(f"Error in fast document search: {e}")
        return {
            "status": "error",
            "message": f"Fast search failed: {str(e)}",
            "organization": config.org_name,
        }


async def _get_document_by_id_impl(
    web_url: str,
    item_id: str,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve document content using web URL and item ID from search results.

    Use this when the document is in a location outside the main SharePoint site
    and {dept}_get_sharepoint_document_content fails.

    Args:
        web_url: The webUrl field from search results
        item_id: The id field from search results
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with document content
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized",
            "message": "Server not initialized with department configuration",
        }

    try:
        import time

        start_time = time.time()

        # Get authentication token
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # STRICT AUTHENTICATION CHECK
        if config.use_delegated_access:
            if (
                not effective_token
                or effective_token == "user_token_placeholder"
                or not effective_token.strip()
            ):
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }

        # Get access token
        if config.use_delegated_access:
            access_token = await oauth_client.get_access_token(effective_token)
        else:
            access_token = await oauth_client.get_application_token()

        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token",
                "organization": config.org_name,
            }

        # Retrieve document content using the new method
        success, content_data = await oauth_client.get_document_content_by_url(
            access_token=access_token,
            web_url=web_url,
            item_id=item_id,
        )

        if not success:
            error_info = content_data.get("error", "Unknown error")
            status_code = content_data.get("status_code", 500)
            return {
                "status": "error",
                "web_url": web_url,
                "item_id": item_id,
                "error": error_info,
                "status_code": status_code,
                "message": f"Failed to retrieve document: {error_info}",
                "organization": config.org_name,
            }

        # Calculate performance
        end_time = time.time()
        processing_time = end_time - start_time

        file_name = content_data.get("name", "Unknown")
        content_text = content_data.get("content", "")

        # Performance logging
        perf_message = f"📄 Retrieved '{file_name}' by ID in {round(processing_time, 2)}s ({len(content_text)} chars)"
        logger.info(perf_message)

        return {
            "status": "success",
            "file_name": file_name,
            "content": content_text,
            "size_bytes": content_data.get("size", 0),
            "mime_type": content_data.get("mime_type", ""),
            "web_url": web_url,
            "organization": config.org_name,
            "processing_time_seconds": round(processing_time, 2),
            "message": f"✅ Retrieved document content ({len(content_text)} characters)",
        }

    except Exception as e:
        logger.error(f"Error retrieving document by ID: {e}")
        return {
            "status": "error",
            "message": f"Document retrieval failed: {str(e)}",
            "web_url": web_url,
            "item_id": item_id,
            "organization": config.org_name,
        }


async def _analyze_all_documents_for_content_impl(
    search_terms: str,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get ALL documents and analyze each one for the search terms using highly optimized parallel processing.
    This uses concurrent processing with minimal logging for maximum speed.
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized",
            "message": "Server not initialized with department configuration",
        }

    try:
        import time

        start_time = time.time()

        # Get user token from parameter or environment variable
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # STRICT AUTHENTICATION CHECK: If delegated access is enabled, user token is REQUIRED
        if config.use_delegated_access:
            if (
                not effective_token
                or effective_token == "user_token_placeholder"
                or not effective_token.strip()
            ):
                return {
                    "status": "error",
                    "error": "Authentication required",
                    "message": DELEGATED_ACCESS_AUTH_ERROR,
                    "organization": config.org_name,
                    "delegated_access_enabled": True,
                    "authentication_failed": True,
                }

        # Get all documents using comprehensive traversal (no verbose logging)
        all_docs_result = await _get_all_documents_comprehensive_impl(effective_token)

        if all_docs_result.get("status") != "success":
            return all_docs_result

        all_documents = all_docs_result.get("documents", [])
        total_docs = len(all_documents)
        folders_processed = all_docs_result.get("folders_processed", 0)

        # Use highly parallel processing for much faster analysis with crash prevention
        try:
            relevant_documents = await _analyze_documents_parallel_ultra_fast(
                all_documents, search_terms, effective_token
            )

            # Ensure we have a valid list
            if not isinstance(relevant_documents, list):
                relevant_documents = []

        except Exception as analysis_error:
            logger.error(f"Document analysis crashed: {str(analysis_error)}")
            return {
                "status": "error",
                "message": f"Document analysis failed: {str(analysis_error)}",
                "organization": config.org_name,
                "crash_prevention": "Applied",
            }

        # Calculate performance metrics
        end_time = time.time()
        processing_time = end_time - start_time

        # Sort by relevance score (highest first)
        relevant_documents.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Simple response size limiting (remove double truncation that causes slowdown)
        limited_results = relevant_documents[:25]

        # Light content limiting - increased preview size to capture early pages of documents
        for doc in limited_results:
            if "content_preview" in doc:
                doc["content_preview"] = (
                    doc["content_preview"][:2000]
                    + "..."  # Increased to 2000 chars for multi-page content
                    if len(doc["content_preview"]) > 2000
                    else doc["content_preview"]
                )
            if "matches" in doc:
                doc["matches"] = doc["matches"][:7]  # Increased to 7 matches

        # FORCE performance logging - short message to prevent truncation
        perf_message = f"🚀 {folders_processed}F/{total_docs}D in {round(processing_time, 1)}s → {len(relevant_documents)} results"
        logger.info(perf_message)
        print(perf_message)

        # Also log to stderr for guaranteed visibility
        import sys

        print(perf_message, file=sys.stderr)

        # Build response with aggressive size control
        response = {
            "status": "success",
            "search_terms": search_terms,
            "documents_analyzed": total_docs,
            "relevant_documents": limited_results,
            "total_relevant": len(relevant_documents),
            "organization": config.org_name,
            "processing_time_seconds": round(processing_time, 1),
            "message": f"🚀 ANALYSIS COMPLETE: {folders_processed} folders, {total_docs} docs in {round(processing_time, 1)}s → {len(relevant_documents)} results (top {len(limited_results)})",
        }

        # Simple, fast response - no more double truncation

        # FINAL PERFORMANCE SUMMARY - appears after all processing
        final_summary = f"\n🚀 FINAL: {folders_processed} folders, {total_docs} documents → {round(processing_time, 1)}s total → {len(relevant_documents)} results"
        print(final_summary)
        logger.info(final_summary.strip())

        return response

    except Exception as e:
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)}",
            "organization": config.org_name,
        }


async def _analyze_documents_parallel_ultra_fast(
    documents: List[Dict], search_terms: str, user_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Ultra-fast parallel document analysis with minimal logging and optimized performance."""
    relevant_documents = []
    max_workers = min(
        20, max(8, len(documents) // 3)
    )  # AGGRESSIVE: Up to 20 workers for maximum speed

    # Global content cache with locks
    content_cache = {}
    cache_hits = 0

    async def _process_document_fast(doc_info: Dict) -> Optional[Dict]:
        """Fast document processing with optimized content retrieval."""
        nonlocal cache_hits

        try:
            doc_name = doc_info.get("name", "Unknown")
            folder_path = doc_info.get("folder_path", "")

            # SPEED BOOST: Skip obviously irrelevant files by extension only
            filename_lower = doc_name.lower()
            search_words_lower = [w.lower() for w in search_terms.split() if len(w) > 2]

            # Skip only non-document files (keep all actual documents for content analysis)
            if not any(
                ext in filename_lower
                for ext in [".pdf", ".docx", ".doc", ".xlsx", ".pptx", ".txt"]
            ):
                return None  # Skip only non-document files

            # Quick filename relevance check
            search_lower = search_terms.lower()
            filename_score = 20 if search_lower in doc_name.lower() else 0

            # Check cache to avoid re-downloading same document within this query
            cache_key = f"{folder_path}::{doc_name}"
            if cache_key in content_cache:
                content = content_cache[cache_key]
                cache_hits += 1
            else:
                # Get document content - SILENT (no OAuth logging)
                import logging

                oauth_logger = logging.getLogger("sharepoint_oauth")
                dept_logger = logging.getLogger(
                    f"{config.department_prefix}-SharePoint"
                )
                original_level_oauth = oauth_logger.level
                original_level_dept = dept_logger.level
                oauth_logger.setLevel(logging.ERROR)  # Suppress OAuth logs
                dept_logger.setLevel(logging.ERROR)  # Suppress dept logs

                try:
                    content_result = await _get_sharepoint_document_content_impl(
                        folder_path, doc_name, user_token
                    )
                    content = (
                        content_result.get("content", "")
                        if content_result.get("status") == "success"
                        else ""
                    )
                    content_cache[cache_key] = content
                finally:
                    # Restore original log levels
                    oauth_logger.setLevel(original_level_oauth)
                    dept_logger.setLevel(original_level_dept)

            if not content and filename_score == 0:
                return None

            # Fast content analysis
            content_lower = content.lower()
            search_words = [
                w.strip() for w in search_lower.split() if len(w.strip()) > 2
            ]

            # Score document relevance
            relevance_score = filename_score
            matches = []

            # Exact phrase match (highest priority)
            if search_lower in content_lower:
                relevance_score += 30
                # Get snippet around exact match
                idx = content_lower.find(search_lower)
                snippet = content[
                    max(0, idx - 40) : idx + len(search_terms) + 40
                ].strip()
                matches.append(snippet)

            # Individual word scoring
            for word in search_words:
                count = min(content_lower.count(word), 6)  # Cap count
                if count > 0:
                    relevance_score += count * 1.5

                    # Get one snippet per word (for speed)
                    if len(matches) < 4:
                        pos = content_lower.find(word)
                        if pos != -1:
                            snippet = content[
                                max(0, pos - 25) : pos + len(word) + 25
                            ].strip()
                            if snippet and snippet not in matches:
                                matches.append(snippet)

            # Return result if relevant
            if relevance_score > 0:
                return {
                    "document": {
                        "name": doc_info.get("name", "Unknown"),
                        "id": doc_info.get("id", ""),
                        "webUrl": doc_info.get("webUrl", ""),
                        "folder_path": doc_info.get("folder_path", ""),
                        "size": doc_info.get("size", 0),
                    },
                    "relevance_score": relevance_score,
                    "content_preview": _get_optimized_content_preview(content),
                    "matches": matches[:3],  # Reduced from 6 to 3
                    "organization": config.org_name,
                }

            return None

        except Exception:
            return None

    # Process documents with asyncio semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_workers)

    async def _process_with_semaphore(doc_info):
        async with semaphore:
            try:
                # SPEED: Much shorter timeout for faster processing
                return await asyncio.wait_for(
                    _process_document_fast(doc_info),
                    timeout=15.0,  # Reduced to 15 seconds for speed
                )
            except asyncio.TimeoutError:
                return None  # Handle timeout gracefully
            except Exception:
                return None  # Silently handle any processing errors

    # Create all tasks and process them concurrently with robust error handling
    tasks = [_process_with_semaphore(doc_info) for doc_info in documents]

    # Process all tasks concurrently with progress tracking and error resilience
    results = []
    high_quality_count = 0

    try:
        # Use asyncio.as_completed for concurrent processing
        completed_count = 0
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                completed_count += 1

                if result:
                    relevant_documents.append(result)
                    if result["relevance_score"] > 15:
                        high_quality_count += 1

                    # AGGRESSIVE early termination for blazing speed
                    if high_quality_count >= 8 and len(relevant_documents) >= 12:
                        # Cancel remaining tasks IMMEDIATELY for speed
                        for task in tasks:
                            if not task.done():
                                try:
                                    task.cancel()
                                except Exception:
                                    pass
                        break  # Exit immediately

            except Exception:
                # Continue processing even if individual tasks fail
                continue

    except Exception:
        # If the entire processing fails, return what we have so far
        pass

    return relevant_documents


def _get_optimized_content_preview(content: str) -> str:
    """Ultra-fast content preview - no regex, just simple truncation for speed."""
    if not content:
        return ""

    # Much smaller preview to prevent MCP response size issues
    if len(content) <= 300:
        return content

    # Just take first 300 characters and add ellipsis
    return content[:300] + "..."


async def _check_sharepoint_permissions_impl(
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check SharePoint connection status and user permissions.

    Args:
        user_token: Optional user access token for delegated access testing

    Returns:
        JSON response with connection status and permission details
    """
    if not config or not oauth_client:
        return {
            "status": "error",
            "error": "Server not initialized with department configuration",
            "message": "Please initialize server with a valid department prefix",
        }

    try:
        logger.info(
            f"Checking {config.org_name} SharePoint permissions and connection status"
        )

        # Get user token from parameter or environment variable
        effective_token = user_token or os.getenv("USER_JWT_TOKEN")

        # Test OAuth connection with OBO flow
        test_result = await oauth_client.test_connection(effective_token)

        return {
            "status": "success",
            "connection_test": test_result,
            "organization": config.org_name,
            "configuration": {
                "client_id": (
                    oauth_client.client_id[:8] + "..."
                    if oauth_client.client_id
                    else "missing"
                ),
                "tenant_id": oauth_client.tenant_id,
                "site_url": oauth_client.site_url,
                "delegated_access": oauth_client.use_delegated_access,
                "obo_scope": oauth_client.obo_scope,
                "default_folders": config.default_search_folders,
            },
            "authentication": "Microsoft Graph API with On-Behalf-Of flow",
            "message": f"{config.org_name} SharePoint permissions check completed",
        }

    except Exception as e:
        logger.error(f"Error checking {config.org_name} SharePoint permissions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to check {config.org_name} SharePoint permissions",
            "organization": config.org_name,
        }


# ===== EMBEDDED DOCUMENT PARSING FUNCTIONS =====


async def parse_document_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse document content using embedded parsers based on file type.

    Args:
        content: Raw document content bytes
        file_name: Name of the file to determine parsing method

    Returns:
        Extracted text content as string
    """
    try:
        file_ext = file_name.lower().split(".")[-1] if "." in file_name else ""

        # Parse silently - no logging during parallel processing
        if file_ext == "pdf":
            return await parse_pdf_content_embedded(content, file_name)
        elif file_ext in ["docx", "doc"]:
            return await parse_word_content_embedded(content, file_name)
        elif file_ext in ["pptx", "ppt"]:
            return await parse_pptx_content_embedded(content, file_name)
        elif file_ext in ["txt", "csv", "text"]:
            return await parse_text_content_embedded(content, file_name)
        else:
            return await parse_generic_content_embedded(content, file_name)

    except Exception as e:
        logger.error(f"Error parsing document {file_name}: {e}")
        return f"Error parsing document: {str(e)}"


async def parse_pdf_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse PDF content using pypdf and pdfplumber (embedded implementation).

    Args:
        content: PDF content bytes
        file_name: Name of the PDF file

    Returns:
        Extracted text content
    """
    try:
        from io import BytesIO

        # First try pypdf (if available)
        try:
            import pypdf

            pdf_stream = BytesIO(content)
            reader = pypdf.PdfReader(pdf_stream)

            text_content = []
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---")
                        text_content.append(text.strip())
                except Exception as page_error:
                    logger.warning(
                        f"Error extracting page {page_num + 1} from {file_name}: {page_error}"
                    )
                    continue

            if text_content:
                extracted_text = "\n\n".join(text_content)
                return extracted_text

        except (ImportError, Exception):
            pass  # Silent fallback

        # Fallback to pdfplumber
        try:
            import pdfplumber

            pdf_stream = BytesIO(content)
            text_content = []

            with pdfplumber.open(pdf_stream) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            text_content.append(f"--- Page {page_num + 1} ---")
                            text_content.append(text.strip())
                    except Exception:
                        continue  # Silent skip on page errors "\n\n".join(text_content)
                return extracted_text

        except Exception:
            pass  # Silent failure

        return f"Unable to extract text from PDF {file_name}. Both pypdf and pdfplumber failed."

    except Exception:
        return f"Error parsing PDF {file_name}"


async def parse_word_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse Word document content using python-docx (embedded implementation).

    Args:
        content: Word document content bytes
        file_name: Name of the Word file

    Returns:
        Extracted text content
    """
    try:
        from io import BytesIO
        import zipfile
        import xml.etree.ElementTree as ET

        # Parse DOCX as ZIP file and extract text from document.xml
        try:
            docx_stream = BytesIO(content)
            with zipfile.ZipFile(docx_stream, "r") as zip_file:
                # Read the main document content
                doc_xml = zip_file.read("word/document.xml")

                # Parse XML and extract text
                root = ET.fromstring(doc_xml)

                # Find all text elements (namespace handling)
                namespace = {
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                }
                text_elements = root.findall(".//w:t", namespace)

                text_content = []
                for elem in text_elements:
                    if elem.text:
                        text_content.append(elem.text)

                extracted_text = "".join(text_content)
                return extracted_text

        except Exception:
            return f"Error parsing Word document {file_name}"

    except Exception:
        return f"Error parsing Word document {file_name}"


async def parse_pptx_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse PowerPoint document content using python-pptx (embedded implementation).

    Args:
        content: PowerPoint document content bytes
        file_name: Name of the PowerPoint file

    Returns:
        Extracted text content from all slides
    """
    try:
        from io import BytesIO
        from pptx import Presentation

        # Parse PPTX
        pptx_stream = BytesIO(content)
        prs = Presentation(pptx_stream)

        text_content = []

        # Extract text from all slides
        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_text = []
            slide_text.append(f"--- Slide {slide_num} ---")

            # Extract text from all shapes in the slide
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())

            if len(slide_text) > 1:  # Has more than just the slide number header
                text_content.append("\n".join(slide_text))

        if text_content:
            extracted_text = "\n\n".join(text_content)
            return extracted_text
        else:
            return f"No text content found in PowerPoint file {file_name}"

    except ImportError:
        return f"python-pptx library not available. Cannot parse {file_name}"
    except Exception as e:
        logger.warning(f"Error parsing PowerPoint document {file_name}: {e}")
        return f"Error parsing PowerPoint document {file_name}: {str(e)}"


async def parse_text_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse plain text content (embedded implementation).

    Args:
        content: Text content bytes
        file_name: Name of the text file

    Returns:
        Decoded text content
    """
    try:
        # Try different encodings
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                decoded_text = content.decode(encoding)
                return decoded_text.strip()
            except UnicodeDecodeError:
                continue

        # Silent fallback to utf-8 with error handling
        decoded_text = content.decode("utf-8", errors="ignore")
        return decoded_text

    except Exception:
        return f"Error parsing text file {file_name}"


async def parse_generic_content_embedded(content: bytes, file_name: str) -> str:
    """
    Parse generic/unknown content types (embedded implementation).

    Args:
        content: Content bytes
        file_name: Name of the file

    Returns:
        Best-effort text extraction
    """
    try:
        # Try to decode as text first
        try:
            decoded_text = content.decode("utf-8", errors="ignore")
            # Filter out non-printable characters for better readability
            import re

            cleaned_text = re.sub(
                r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]", "", decoded_text
            )

            if len(cleaned_text.strip()) > 10:  # If we got reasonable text
                return cleaned_text
        except Exception as decode_error:
            logger.warning(f"Could not decode {file_name} as text: {decode_error}")

        # If text extraction failed, provide file info
        file_size = len(content)
        return f"Binary file {file_name} ({file_size} bytes). Content type not supported for text extraction."

    except Exception as e:
        logger.error(f"Error in generic content parsing for {file_name}: {e}")
        return f"Error parsing file {file_name}: {str(e)}"


def register_department_tools(department_prefix: str):
    dept_lower = department_prefix.lower()

    # ------------------ LIST FOLDER CONTENTS ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_list_folder_contents",
        description=f"List all files and folders in a specific SharePoint folder path for {department_prefix}. Use this when you need to list or count files in a specific folder (not search for content). Provide the folder path like 'Canchat Demo' or 'Documents/Reports' or '' for root.",
    )
    async def list_folder(
        folder_path: str,
        user_token: Optional[str] = None,
    ):
        return await _list_folder_contents_impl(folder_path, user_token)

    # ------------------ FAST SEARCH (NEW - RECOMMENDED) ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_search_documents_fast",
        description=f"FAST search in {department_prefix} SharePoint using Microsoft Graph Search API with KQL support (sub-1 second). Results sorted by relevance. Supports plain text or KQL queries like 'filename:*.pdf AND railway' or 'lastModifiedTime>=2024-01-01 AND infrastructure'",
    )
    async def search_fast(
        query: str,
        limit: int = 25,
        user_token: Optional[str] = None,
    ):
        return await _search_documents_fast_impl(query, limit, user_token)

    # ------------------ Get Document by ID (from search results) ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_get_document_by_id",
        description=f"Retrieve document content from {department_prefix} SharePoint using web URL and item ID from search results. Use this when {dept_lower}_get_sharepoint_document_content fails (404 errors) because the document is in a different location. Pass the 'webUrl' and 'id' fields directly from search results.",
    )
    async def get_document_by_id(
        web_url: str,
        item_id: str,
        user_token: Optional[str] = None,
    ):
        return await _get_document_by_id_impl(web_url, item_id, user_token)

    # ------------------ Document Content ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_get_sharepoint_document_content",
        description=f"Retrieve a document from {department_prefix} SharePoint",
    )
    async def get_document(
        folder_name: str,
        file_name: str,
        user_token: Optional[str] = None,
    ):
        return await _get_sharepoint_document_content_impl(
            folder_name, file_name, user_token
        )

    # ------------------ All Documents ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_get_all_documents_comprehensive",
        description=f"Retrieve all documents from {department_prefix} SharePoint",
    )
    async def get_all_documents(
        user_token: Optional[str] = None,
    ):
        return await _get_all_documents_comprehensive_impl(user_token)

    # ------------------ Analyze Documents (SLOW - Use search_fast instead) ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_analyze_all_documents_for_content",
        description=f"[LEGACY - SLOW 20-60s] Analyze all documents in {department_prefix} SharePoint by downloading and parsing each one. USE {dept_lower}_search_documents_fast INSTEAD for much better performance (sub-1 second)",
    )
    async def analyze_documents(
        search_terms: str,
        user_token: Optional[str] = None,
    ):
        return await _analyze_all_documents_for_content_impl(search_terms, user_token)

    # ------------------ Permissions ------------------
    @generic_sharepoint_server.tool(
        name=f"{dept_lower}_check_sharepoint_permissions",
        description=f"Check SharePoint permissions for {department_prefix}",
    )
    async def check_permissions(
        user_token: Optional[str] = None,
    ):
        return await _check_sharepoint_permissions_impl(user_token)


def run_department_server(department_prefix: str):
    department_prefix = department_prefix.upper()

    if not initialize_department_server(department_prefix):
        raise RuntimeError(f"Failed to initialize {department_prefix}")

    register_department_tools(department_prefix)

    logger.info(f"🚀 Starting {department_prefix} SharePoint MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generic SharePoint MCP Server — pass department prefix as argument."
    )
    parser.add_argument(
        "department",
        help="Department prefix, e.g. MPO, PMO, FIN",
    )
    _args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s - {_args.department.upper()}-SharePoint - %(levelname)s - %(message)s",
    )
    run_department_server(_args.department)
