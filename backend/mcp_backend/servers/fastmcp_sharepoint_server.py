#!/usr/bin/env python3
"""
SharePoint MCP Server with On-Behalf-Of (OBO) Flow Support

This server provides SharePoint document search and retrieval capabilities
for the MPO (Major Project Office) integration with CANchat.

Supports two authentication modes:
1. Application authentication (client credentials) - broad access
2. User-delegated authentication (on-behalf-of) - user-scoped access

Required environment variables:
- SHP_ID_APP: Azure App Registration Client ID
- SHP_ID_APP_SECRET: Azure App Registration Client Secret  
- SHP_TENANT_ID: Azure AD Tenant ID
- SHP_SITE_URL: SharePoint Site URL
- SHP_DOC_LIBRARY: SharePoint Document Library (optional, defaults to 'Shared Documents')
- SHP_USE_DELEGATED_ACCESS: Enable user-scoped access (true/false)
- SHP_OBO_SCOPE: Scopes for On-Behalf-Of token exchange
"""
import os
import sys
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sharepoint_oauth_client import get_oauth_client, SharePointOAuthClient

    # Set required environment variables if they don't exist but our variables do
    if not os.getenv("SHP_ID_APP") and os.getenv("SHAREPOINT_CLIENT_ID"):
        os.environ["SHP_ID_APP"] = os.getenv("SHAREPOINT_CLIENT_ID")
    if not os.getenv("SHP_ID_APP_SECRET") and os.getenv("SHAREPOINT_CLIENT_SECRET"):
        os.environ["SHP_ID_APP_SECRET"] = os.getenv("SHAREPOINT_CLIENT_SECRET")
    if not os.getenv("SHP_TENANT_ID") and os.getenv("SHAREPOINT_TENANT_ID"):
        os.environ["SHP_TENANT_ID"] = os.getenv("SHAREPOINT_TENANT_ID")
    if not os.getenv("SHP_SITE_URL") and os.getenv("SHAREPOINT_SITE_URL"):
        os.environ["SHP_SITE_URL"] = os.getenv("SHAREPOINT_SITE_URL")

    # Initialize OAuth client
    oauth_client = get_oauth_client()

except ImportError as e:
    print(f"Error importing SharePoint OAuth client: {e}")
    sys.exit(1)
except ValueError as e:
    print(f"SharePoint configuration error: {e}")
    print("Please set the required SharePoint environment variables:")
    print("- SHP_ID_APP (or SHAREPOINT_CLIENT_ID)")
    print("- SHP_ID_APP_SECRET (or SHAREPOINT_CLIENT_SECRET)")
    print("- SHP_TENANT_ID (or SHAREPOINT_TENANT_ID)")
    print("- SHP_SITE_URL (or SHAREPOINT_SITE_URL)")
    sys.exit(1)

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastmcp_sharepoint")

# Create FastMCP app instance
sharepoint_server = FastMCP("SharePoint MCP Server")


def extract_user_token(context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Extract user access token from MCP context

    Args:
        context: MCP request context (may contain user token)

    Returns:
        User access token if available, None otherwise
    """
    if not context:
        return None

    # Look for user token in various possible locations
    user_token = (
        context.get("user_token")
        or context.get("access_token")
        or context.get("authorization", {}).get("token")
        or context.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
    )

    return user_token if user_token else None


@sharepoint_server.tool()
async def search_sharepoint_documents(
    query: str = "documents",
    folder_path: Optional[str] = None,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for documents in SharePoint based on a query.

    This tool searches for documents in SharePoint folders. For MPO-related queries,
    it automatically uses the configured MPO folder and searches in Communications
    subfolders for better document discovery.

    Args:
        query: Search terms to find relevant documents (e.g., "transformative strategies")
        folder_path: SharePoint folder path to search in (uses SHP_DOC_LIBRARY env var if not provided)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with search results and document list
    """
    try:
        # Use environment variable or default for folder path
        if folder_path is None:
            folder_path = os.getenv("SHP_DOC_LIBRARY", "Major Projects Office (MPO)")

        logger.info(f"Searching SharePoint for: {query} in folder: {folder_path}")

        # Get appropriate access token
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "query": query,
                "folder": folder_path,
                "error": "Failed to obtain access token",
                "message": "Authentication failed. Check your configuration.",
            }

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "query": query,
                "folder": folder_path,
                "error": site_info,
                "message": "Failed to access SharePoint site",
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "query": query,
                "folder": folder_path,
                "error": drives_data,
                "message": "Failed to access document libraries",
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "query": query,
                "folder": folder_path,
                "error": "No document libraries found",
                "message": "No accessible document libraries found",
            }

        # Use first drive for now (could be enhanced to search specific library)
        drive_id = drives[0].get("id")

        # Get documents from the specified folder
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_path
        )

        # If we successfully accessed the folder, check if it has a Communications subfolder
        # (This is common for organizational folders like MPO)
        if success:
            items = items_data.get("value", [])

            # Look for Communications subfolder in the main folder
            communications_folder = None

            # First pass: look for exact "Communications" match
            for item in items:
                if (
                    item.get("folder")
                    and item.get("name", "").lower() == "communications"
                ):
                    communications_folder = item
                    break

            # Second pass: look for close matches if no exact match found
            if not communications_folder:
                for item in items:
                    name_lower = item.get("name", "").lower()
                    if item.get("folder") and (
                        name_lower == "communication"
                        or (
                            name_lower.startswith("comm")
                            and len(name_lower) <= 15
                            and "communication" in name_lower
                        )
                    ):
                        communications_folder = item
                        break

            # If we found a Communications folder, search there instead
            if communications_folder:
                comm_folder_name = f"{folder_path}/{communications_folder.get('name')}"
                logger.info(
                    f"Found Communications subfolder, searching in: {comm_folder_name}"
                )

                comm_success, comm_items = await oauth_client.get_drive_items(
                    access_token, site_id, drive_id, comm_folder_name
                )
                if comm_success:
                    items_data = comm_items
                    folder_path = comm_folder_name  # Update folder path for response
                    logger.info(
                        f"Successfully switched to Communications folder with {len(comm_items.get('value', []))} items"
                    )
                else:
                    logger.warning(
                        f"Found Communications folder but couldn't access it: {comm_folder_name}"
                    )

        if not success:
            # If the exact folder path fails, try searching in subfolders
            logger.info(
                f"Direct folder search failed, attempting to find subfolders..."
            )

            # Get items from parent folder (root or Documents)
            parent_success, parent_items = await oauth_client.get_drive_items(
                access_token, site_id, drive_id, ""
            )
            if parent_success:
                items = parent_items.get("value", [])

                # Look for folders that might contain our target folder
                for item in items:
                    if (
                        item.get("folder")
                        and folder_path.lower() in item.get("name", "").lower()
                    ):
                        # Try searching in this folder
                        subfolder_name = item.get("name")
                        logger.info(f"Trying subfolder: {subfolder_name}")

                        sub_success, sub_items = await oauth_client.get_drive_items(
                            access_token, site_id, drive_id, subfolder_name
                        )
                        if sub_success:
                            # Check if this subfolder has Communications or similar
                            sub_folders = sub_items.get("value", [])

                            # First pass: look for exact matches
                            communications_folder = None
                            for sub_item in sub_folders:
                                sub_name_lower = sub_item.get("name", "").lower()
                                if (
                                    sub_item.get("folder")
                                    and sub_name_lower == "communications"
                                ):
                                    communications_folder = sub_item
                                    break

                            # Second pass: look for close matches if no exact match found
                            if not communications_folder:
                                for sub_item in sub_folders:
                                    sub_name_lower = sub_item.get("name", "").lower()
                                    if sub_item.get("folder") and (
                                        sub_name_lower == "communication"
                                        or (
                                            sub_name_lower.startswith("comm")
                                            and len(sub_name_lower) <= 15
                                            and "communication" in sub_name_lower
                                        )
                                    ):
                                        communications_folder = sub_item
                                        break

                            if communications_folder:
                                comm_folder_name = f"{subfolder_name}/{communications_folder.get('name')}"
                                logger.info(
                                    f"Found communications folder: {comm_folder_name}"
                                )

                                comm_success, comm_items = (
                                    await oauth_client.get_drive_items(
                                        access_token,
                                        site_id,
                                        drive_id,
                                        comm_folder_name,
                                    )
                                )
                                if comm_success:
                                    items_data = comm_items
                                    success = True
                                    folder_path = comm_folder_name  # Update folder path for response
                                    break

                            if success:
                                break
                            else:
                                # If no Communications subfolder, use the main folder
                                items_data = sub_items
                                success = True
                                folder_path = subfolder_name
                                break

            if not success:
                return {
                    "status": "error",
                    "query": query,
                    "folder": folder_path,
                    "error": items_data,
                    "message": "Failed to find and list documents in folder or subfolders",
                }

        items = items_data.get("value", [])

        # Filter items based on query with more flexible matching
        matching_documents = []
        for item in items:
            if item.get("file"):  # Only include files, not folders
                name = item.get("name", "")
                # More flexible matching - check for individual words in the query
                query_words = query.lower().split()
                name_lower = name.lower()

                # Match if any significant word from query appears in filename
                match_found = False
                for word in query_words:
                    if (
                        len(word) > 2 and word in name_lower
                    ):  # Skip very short words like "a", "of"
                        match_found = True
                        break

                # Also check for exact phrase match
                if query.lower() in name_lower:
                    match_found = True

                if match_found:
                    matching_documents.append(
                        {
                            "name": name,
                            "id": item.get("id"),
                            "size": item.get("size"),
                            "lastModified": item.get("lastModifiedDateTime"),
                            "webUrl": item.get("webUrl"),
                            "folder_path": folder_path,  # Include the actual folder path found
                        }
                    )

        return {
            "status": "success",
            "query": query,
            "folder": folder_path,
            "total_items": len(items),
            "matching_documents": matching_documents,
            "match_count": len(matching_documents),
            "site_name": site_info.get("displayName"),
            "drive_name": drives[0].get("name"),
            "exploration_suggestion": "For project counts and detailed information, consider using the 'list_sharepoint_folder_contents' tool to explore subfolders like 'Projects', 'Prospects', or 'Transformative Strategies'.",
            "message": f"Found {len(matching_documents)} documents matching '{query}' in {folder_path}. Use folder exploration for project counts.",
        }

    except Exception as e:
        logger.error(f"Error searching SharePoint documents: {e}")
        return {
            "status": "error",
            "query": query,
            "folder": folder_path,
            "error": str(e),
            "message": "Failed to search SharePoint documents. Please check your configuration and permissions.",
        }


@sharepoint_server.tool()
async def get_sharepoint_document_content(
    folder_name: str, file_name: str, user_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve the content of a specific SharePoint document.

    Args:
        folder_name: SharePoint folder containing the document
        file_name: Name of the document file
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with document content and metadata
    """
    try:
        logger.info(f"Getting content for: {file_name} in folder: {folder_name}")

        # Get appropriate access token
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": "Failed to obtain access token",
                "message": "Authentication failed",
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
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": "No document libraries found",
                "message": "No accessible document libraries found",
            }

        drive_id = drives[0].get("id")

        # Construct file path
        if folder_name and folder_name != "/":
            file_path = f"{folder_name}/{file_name}"
        else:
            file_path = file_name

        # Get file content
        success, content = await oauth_client.get_file_content(
            access_token, site_id, drive_id, file_path
        )
        if not success:
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": content,
                "message": "Failed to retrieve document content",
            }

        # Convert binary content to text (basic implementation)
        try:
            if isinstance(content, bytes):
                # Try UTF-8 decoding first
                try:
                    text_content = content.decode("utf-8")
                except UnicodeDecodeError:
                    # If UTF-8 fails, it's likely a binary document
                    file_extension = (
                        file_name.split(".")[-1].lower()
                        if "." in file_name
                        else "unknown"
                    )

                    # Provide helpful information about the binary file
                    if file_extension in ["pdf"]:
                        text_content = f"[PDF Document - {len(content)} bytes]\n\nThis is a PDF file that requires PDF text extraction tools. The document may contain:\n- Text content that needs OCR or PDF parsing\n- Charts, graphs, or images\n- Structured data like project counts or statistics\n\nTo access the full content, open the SharePoint link or use PDF extraction tools."
                    elif file_extension in ["docx", "doc"]:
                        text_content = f"[Microsoft Word Document - {len(content)} bytes]\n\nThis is a Word document that requires document parsing tools. The document may contain:\n- Formatted text with project information\n- Tables with project counts or data\n- Embedded charts or images\n\nTo access the full content, open the SharePoint link or use Word document extraction tools."
                    elif file_extension in ["xlsx", "xls"]:
                        text_content = f"[Microsoft Excel Spreadsheet - {len(content)} bytes]\n\nThis is an Excel spreadsheet that may contain:\n- Project data in tabular format\n- Project counts and statistics\n- Financial or tracking information\n- Multiple worksheets with different data\n\nTo access the full content, open the SharePoint link or use Excel parsing tools."
                    else:
                        text_content = f"[Binary file - {len(content)} bytes]\n\nFile type: {file_extension.upper()}\nThis file requires appropriate tools to extract readable content."
            else:
                text_content = str(content)
        except Exception:
            text_content = f"[Binary file - {len(content) if isinstance(content, bytes) else 'unknown'} bytes]"

        return {
            "status": "success",
            "folder": folder_name,
            "file": file_name,
            "content": text_content,
            "size": len(content) if isinstance(content, bytes) else len(str(content)),
            "site_name": site_info.get("displayName"),
            "message": f"Successfully retrieved content for {file_name}",
        }

    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        return {
            "status": "error",
            "folder": folder_name,
            "file": file_name,
            "error": str(e),
            "message": "Failed to retrieve document content",
        }


@sharepoint_server.tool()
async def list_sharepoint_sites(user_token: Optional[str] = None) -> Dict[str, Any]:
    """
    List available SharePoint folders and get site structure.

    Args:
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with SharePoint site structure and available folders
    """
    try:
        logger.info("Listing SharePoint site structure")

        # Get appropriate access token
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "error": "Failed to obtain access token",
                "message": "Authentication failed",
            }

        # Get site and drives information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "error": site_info,
                "message": "Failed to access SharePoint site",
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "error": drives_data,
                "message": "Failed to list document libraries",
            }

        drives = drives_data.get("value", [])

        # Get root items for each drive
        drive_contents = []
        for drive in drives[:3]:  # Limit to first 3 drives to avoid too much data
            drive_id = drive.get("id")
            success, items_data = await oauth_client.get_drive_items(
                access_token, site_id, drive_id, ""
            )
            if success:
                items = items_data.get("value", [])
                folders = [item for item in items if item.get("folder")]
                files = [item for item in items if item.get("file")]

                drive_contents.append(
                    {
                        "drive_name": drive.get("name"),
                        "drive_id": drive.get("id"),
                        "folder_count": len(folders),
                        "file_count": len(files),
                        "folders": [
                            f.get("name") for f in folders[:10]
                        ],  # First 10 folders
                        "files": [f.get("name") for f in files[:10]],  # First 10 files
                    }
                )

        return {
            "status": "success",
            "site_url": oauth_client.site_url,
            "site_name": site_info.get("displayName"),
            "site_id": site_id,
            "drives_count": len(drives),
            "drives": [{"name": d.get("name"), "id": d.get("id")} for d in drives],
            "drive_contents": drive_contents,
            "access_mode": (
                "delegated" if oauth_client.use_delegated_access else "application"
            ),
            "message": "Successfully retrieved SharePoint site structure",
        }

    except Exception as e:
        logger.error(f"Error listing SharePoint sites: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to list SharePoint sites",
        }


@sharepoint_server.tool()
async def check_sharepoint_status(user_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Check SharePoint connection status and configuration.

    Args:
        user_token: Optional user access token for delegated access testing

    Returns:
        JSON response with connection status and configuration details
    """
    try:
        logger.info("Checking SharePoint connection status")

        # Test OAuth connection
        test_result = await oauth_client.test_connection(user_token)

        return {
            "status": "success",
            "connection_test": test_result,
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
            },
            "message": "SharePoint status check completed",
        }

    except Exception as e:
        logger.error(f"Error checking SharePoint status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check SharePoint status",
        }


@sharepoint_server.tool()
async def get_sharepoint_search_results(
    search_term: str,
    folder_name: Optional[str] = None,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Advanced search for SharePoint documents with content filtering.

    This tool provides advanced document search capabilities. For MPO-related queries
    (Major Projects Office), it automatically searches in the MPO folder and Communications
    subfolder where most MPO documents are stored.

    Args:
        search_term: Term to search for in document names and content (e.g., "MPO transformative strategies")
        folder_name: Folder to search within. Use "Major Projects Office (MPO)" for MPO-related documents.
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with filtered search results including document metadata and links
    """
    try:
        # Use environment variable or default for folder name
        if folder_name is None:
            folder_name = os.getenv("SHP_DOC_LIBRARY", "Major Projects Office (MPO)")

        logger.info(f"Advanced search for: {search_term} in folder: {folder_name}")

        # Reuse the search functionality from search_sharepoint_documents
        result = await search_sharepoint_documents(search_term, folder_name, user_token)

        # Add search-specific metadata
        if result.get("status") == "success":
            result["search_type"] = "advanced"
            result["original_search_term"] = search_term

        return result

    except Exception as e:
        logger.error(f"Error in advanced SharePoint search: {e}")
        return {
            "status": "error",
            "search_term": search_term,
            "folder_name": folder_name,
            "error": str(e),
            "message": "Failed to perform advanced SharePoint search",
        }


@sharepoint_server.tool()
async def list_sharepoint_folder_contents(
    folder_path: Optional[str] = None, user_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    List the contents of a SharePoint folder to explore structure and find project information.

    This tool helps explore SharePoint folder structures, including subfolders like
    'Prospects', 'Projects', and 'Transformative Strategies' to get counts and organization.

    Args:
        folder_path: SharePoint folder path to explore (uses SHP_DOC_LIBRARY env var if not provided)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with folder contents, subfolder counts, and file listings
    """
    try:
        # Use environment variable or default for folder path
        if folder_path is None:
            folder_path = os.getenv("SHP_DOC_LIBRARY", "Major Projects Office (MPO)")

        logger.info(f"Listing SharePoint folder contents: {folder_path}")

        # Get appropriate access token
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "folder": folder_path,
                "error": "Failed to obtain access token",
                "message": "Authentication failed. Check your configuration.",
            }

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "folder": folder_path,
                "error": site_info,
                "message": "Failed to access SharePoint site",
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "folder": folder_path,
                "error": drives_data,
                "message": "Failed to access document libraries",
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "folder": folder_path,
                "error": "No document libraries found",
                "message": "No accessible document libraries found",
            }

        # Use first drive
        drive_id = drives[0].get("id")

        # Get folder contents
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_path
        )
        if not success:
            return {
                "status": "error",
                "folder": folder_path,
                "error": items_data,
                "message": "Failed to access folder contents",
            }

        items = items_data.get("value", [])

        # Organize contents
        folders = []
        files = []

        for item in items:
            if item.get("folder"):
                folder_info = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "lastModified": item.get("lastModifiedDateTime"),
                    "webUrl": item.get("webUrl"),
                    "childCount": item.get("folder", {}).get("childCount", 0),
                }
                folders.append(folder_info)
            else:
                file_info = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "size": item.get("size"),
                    "lastModified": item.get("lastModifiedDateTime"),
                    "webUrl": item.get("webUrl"),
                    "fileType": (
                        item.get("name", "").split(".")[-1].lower()
                        if "." in item.get("name", "")
                        else "unknown"
                    ),
                }
                files.append(file_info)

        # Calculate summary statistics
        project_folders = [
            f
            for f in folders
            if any(
                keyword in f["name"].lower()
                for keyword in ["project", "prospect", "initiative"]
            )
        ]

        return {
            "status": "success",
            "folder": folder_path,
            "total_items": len(items),
            "folder_count": len(folders),
            "file_count": len(files),
            "folders": folders,
            "files": files,
            "project_related_folders": project_folders,
            "potential_project_count": sum(
                f.get("childCount", 0) for f in project_folders
            ),
            "site_name": site_info.get("displayName"),
            "message": f"Found {len(folders)} folders and {len(files)} files in {folder_path}. Project-related folders: {len(project_folders)}",
        }

    except Exception as e:
        logger.error(f"Error listing folder contents: {e}")
        return {
            "status": "error",
            "folder": folder_path,
            "error": str(e),
            "message": "Failed to list folder contents",
        }


def get_app():
    """Get the FastMCP app instance"""
    return sharepoint_server


if __name__ == "__main__":
    logger.info("Starting SharePoint FastMCP Server with OBO support...")

    # Check configuration before starting
    required_vars = ["SHP_ID_APP", "SHP_ID_APP_SECRET", "SHP_TENANT_ID", "SHP_SITE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error(
            "Please set the required SharePoint environment variables before starting the server"
        )
        sys.exit(1)

    logger.info(f"SharePoint site: {oauth_client.site_url}")
    logger.info(f"Delegated access: {oauth_client.use_delegated_access}")
    logger.info(f"OBO scope: {oauth_client.obo_scope}")

    # Run the FastMCP server
    sharepoint_server.run()
