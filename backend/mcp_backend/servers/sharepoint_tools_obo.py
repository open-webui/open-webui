#!/usr/bin/env python3
"""
SharePoint Tools with Microsoft Graph API + OBO Support

This module provides mcp-sharepoint-compatible tools that use Microsoft Graph API
with On-Behalf-Of flow instead of the office365-rest-python-client library.

This maintains the same tool interfaces as mcp-sharepoint but with OBO authentication.
"""
import os
import sys
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sharepoint_oauth_client import get_oauth_client

    oauth_client = get_oauth_client()
except ImportError as e:
    print(f"Error importing SharePoint OAuth client: {e}")
    sys.exit(1)

logger = logging.getLogger("sharepoint_tools_obo")

# Configuration from environment
SHP_DOC_LIBRARY = os.getenv("SHP_DOC_LIBRARY", "")
ORG_NAME = os.getenv("SHP_ORG_NAME", "Organization")


async def list_documents(
    folder_name: str, user_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all documents in a specified SharePoint folder using Microsoft Graph API.

    Compatible with mcp-sharepoint.tools.list_documents_tool interface.

    Args:
        folder_name: SharePoint folder to list documents from
        user_token: Optional user access token for OBO

    Returns:
        List of document dictionaries with metadata
    """
    try:
        logger.info(f"Listing documents in folder: {folder_name}")

        # Get appropriate access token using OBO flow
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            raise Exception("Failed to obtain access token")

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            raise Exception(f"Failed to access SharePoint site: {site_info}")

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            raise Exception(f"Failed to access document libraries: {drives_data}")

        drives = drives_data.get("value", [])
        if not drives:
            raise Exception("No document libraries found")

        drive_id = drives[0].get("id")

        # Get folder contents
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_name
        )
        if not success:
            raise Exception(f"Failed to access folder contents: {items_data}")

        items = items_data.get("value", [])

        # Filter to only files and format for mcp-sharepoint compatibility
        documents = []
        for item in items:
            if item.get("file"):  # Only files, not folders
                doc = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "size": item.get("size", 0),
                    "modified": item.get("lastModifiedDateTime"),
                    "url": item.get("webUrl"),
                    "serverRelativeUrl": (
                        f"/{folder_name}/{item.get('name')}"
                        if folder_name
                        else f"/{item.get('name')}"
                    ),
                    "file_type": (
                        item.get("name", "").split(".")[-1].lower()
                        if "." in item.get("name", "")
                        else "unknown"
                    ),
                }
                documents.append(doc)

        logger.info(f"Found {len(documents)} documents in {folder_name}")
        return documents

    except Exception as e:
        logger.error(f"Error listing documents in {folder_name}: {e}")
        return []


async def list_folders(
    parent_folder: Optional[str] = None, user_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List folders in the specified SharePoint directory using Microsoft Graph API.

    Compatible with mcp-sharepoint.tools.list_folders_tool interface.

    Args:
        parent_folder: Parent folder to list from (None for root)
        user_token: Optional user access token for OBO

    Returns:
        List of folder dictionaries with metadata
    """
    try:
        folder_path = parent_folder or SHP_DOC_LIBRARY
        logger.info(f"Listing folders in: {folder_path}")

        # Get appropriate access token using OBO flow
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            raise Exception("Failed to obtain access token")

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            raise Exception(f"Failed to access SharePoint site: {site_info}")

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            raise Exception(f"Failed to access document libraries: {drives_data}")

        drives = drives_data.get("value", [])
        if not drives:
            raise Exception("No document libraries found")

        drive_id = drives[0].get("id")

        # Get folder contents
        success, items_data = await oauth_client.get_drive_items(
            access_token, site_id, drive_id, folder_path
        )
        if not success:
            raise Exception(f"Failed to access folder contents: {items_data}")

        items = items_data.get("value", [])

        # Filter to only folders and format for mcp-sharepoint compatibility
        folders = []
        for item in items:
            if item.get("folder"):  # Only folders, not files
                folder = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "modified": item.get("lastModifiedDateTime"),
                    "url": item.get("webUrl"),
                    "serverRelativeUrl": (
                        f"/{folder_path}/{item.get('name')}"
                        if folder_path
                        else f"/{item.get('name')}"
                    ),
                    "childCount": item.get("folder", {}).get("childCount", 0),
                }
                folders.append(folder)

        logger.info(f"Found {len(folders)} folders in {folder_path}")
        return folders

    except Exception as e:
        logger.error(f"Error listing folders in {parent_folder}: {e}")
        return []


async def get_document_content(
    folder_name: str, file_name: str, user_token: Optional[str] = None
) -> str:
    """
    Get content of a document in SharePoint using Microsoft Graph API.

    Compatible with mcp-sharepoint.tools.get_document_content_tool interface.

    Args:
        folder_name: SharePoint folder containing the document
        file_name: Name of the document file
        user_token: Optional user access token for OBO

    Returns:
        Document content as string
    """
    try:
        logger.info(f"Getting content for: {file_name} in folder: {folder_name}")

        # Get appropriate access token using OBO flow
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            raise Exception("Failed to obtain access token")

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            raise Exception(f"Failed to access SharePoint site: {site_info}")

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            raise Exception(f"Failed to access document libraries: {drives_data}")

        drives = drives_data.get("value", [])
        if not drives:
            raise Exception("No document libraries found")

        drive_id = drives[0].get("id")

        # Construct file path
        file_path = f"{folder_name}/{file_name}" if folder_name else file_name

        # Get file content
        success, content = await oauth_client.get_file_content(
            access_token, site_id, drive_id, file_path
        )
        if not success:
            raise Exception(f"Failed to retrieve document content: {content}")

        # Parse document content using existing document engine
        logger.info(f"Starting document parsing for {file_name} using document engine")
        parsed_content = await _parse_document_with_engine(content, file_name)
        logger.info(
            f"Document parsing completed for {file_name}, content length: {len(parsed_content)}"
        )
        return parsed_content

    except Exception as e:
        logger.error(f"Error getting document content for {file_name}: {e}")
        return f"Error retrieving content: {str(e)}"


async def _parse_document_with_engine(content: bytes, file_name: str) -> str:
    """
    Parse document content using the configured document extraction engine.

    Args:
        content: Raw binary content
        file_name: Name of the file to determine parsing method

    Returns:
        Parsed text content
    """
    import tempfile
    import os
    from open_webui.retrieval.loaders.main import Loader
    from open_webui.config import CONTENT_EXTRACTION_ENGINE, TIKA_SERVER_URL

    logger.info(
        f"_parse_document_with_engine called for {file_name}, content size: {len(content)} bytes"
    )

    try:
        if not isinstance(content, bytes):
            logger.info(f"Content is not bytes for {file_name}, returning as string")
            return str(content)

        # Get file extension for MIME type approximation
        file_extension = (
            file_name.split(".")[-1].lower() if "." in file_name else "unknown"
        )
        logger.info(f"File extension: {file_extension}")

        # Map file extensions to MIME types
        mime_type_mapping = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "txt": "text/plain",
            "csv": "text/csv",
            "html": "text/html",
            "xml": "application/xml",
        }

        file_content_type = mime_type_mapping.get(
            file_extension, "application/octet-stream"
        )

        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(
            suffix=f".{file_extension}", delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()

            try:
                # Get current engine configuration
                engine = (
                    CONTENT_EXTRACTION_ENGINE.value
                    if hasattr(CONTENT_EXTRACTION_ENGINE, "value")
                    else str(CONTENT_EXTRACTION_ENGINE)
                )

                # Initialize loader with current engine configuration
                loader_kwargs = {}
                if engine == "tika":
                    tika_url = (
                        TIKA_SERVER_URL.value
                        if hasattr(TIKA_SERVER_URL, "value")
                        else str(TIKA_SERVER_URL)
                    )
                    loader_kwargs["TIKA_SERVER_URL"] = tika_url

                loader = Loader(engine=engine, **loader_kwargs)

                # Load and process document
                documents = loader.load(file_name, file_content_type, temp_file.name)

                if documents:
                    # Combine all document content (usually just one document)
                    combined_content = ""
                    for doc in documents:
                        if hasattr(doc, "page_content"):
                            combined_content += doc.page_content + "\n\n"

                    if combined_content.strip():
                        return combined_content.strip()
                    else:
                        return f"[{file_extension.upper()} Document - {len(content)} bytes]\n\nDocument processed but no text content extracted"
                else:
                    return f"[{file_extension.upper()} Document - {len(content)} bytes]\n\nNo content could be extracted from document"

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass  # Ignore cleanup errors

    except Exception as e:
        logger.error(f"Error parsing document content with engine: {e}")
        # Fallback to basic text extraction for plain text files
        if file_extension in ["txt", "csv", "log"]:
            try:
                return content.decode("utf-8", errors="ignore")
            except Exception:
                pass

        return f"[{file_extension.upper()} Document - {len(content)} bytes]\n\nFailed to parse content with document engine: {str(e)}"


async def get_folder_tree(
    parent_folder: Optional[str] = None,
    max_depth: int = 3,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Iteratively build folder tree using Microsoft Graph API.

    Compatible with mcp-sharepoint.tools.get_sharepoint_tree_tool interface.

    Args:
        parent_folder: Parent folder to start from (None for root)
        max_depth: Maximum depth to traverse
        user_token: Optional user access token for OBO

    Returns:
        Hierarchical folder structure dictionary
    """
    try:
        folder_path = parent_folder or SHP_DOC_LIBRARY
        logger.info(f"Building folder tree for: {folder_path} (max depth: {max_depth})")

        async def build_tree_level(current_folder: str, depth: int) -> Dict[str, Any]:
            """Recursively build tree structure"""
            if depth > max_depth:
                return {}

            folders = await list_folders(current_folder, user_token)
            tree = {}

            for folder in folders:
                folder_name = folder.get("name")
                folder_path = (
                    f"{current_folder}/{folder_name}" if current_folder else folder_name
                )

                # Get children if not at max depth
                if depth < max_depth:
                    children = await build_tree_level(folder_path, depth + 1)
                    tree[folder_name] = children
                else:
                    tree[folder_name] = {}

            return tree

        tree_structure = await build_tree_level(folder_path, 0)

        return {
            "tree": tree_structure,
            "root_folder": folder_path,
            "max_depth": max_depth,
            "organization": ORG_NAME,
        }

    except Exception as e:
        logger.error(f"Error building folder tree: {e}")
        return {"error": str(e)}


# Async wrapper functions to match mcp-sharepoint.tools interface
async def list_documents_tool(
    folder_name: str, user_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List all documents in a specified SharePoint folder - mcp-sharepoint compatible"""
    return await list_documents(folder_name, user_token)


async def list_folders_tool(
    parent_folder: Optional[str] = None, user_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List folders in the specified SharePoint directory - mcp-sharepoint compatible"""
    return await list_folders(parent_folder, user_token)


async def get_document_content_tool(
    folder_name: str, file_name: str, user_token: Optional[str] = None
) -> str:
    """Get content of a document in SharePoint - mcp-sharepoint compatible"""
    return await get_document_content(folder_name, file_name, user_token)


async def get_sharepoint_tree_tool(
    parent_folder: Optional[str] = None, user_token: Optional[str] = None
) -> Dict[str, Any]:
    """Get a recursive tree view of a SharePoint folder - mcp-sharepoint compatible"""
    return await get_folder_tree(parent_folder, 3, user_token)
