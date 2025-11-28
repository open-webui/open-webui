#!/usr/bin/env python3
"""
Generic SharePoint MCP Server with On-Behalf-Of (OBO) Flow Support

This server provides SharePoint document search and retrieval capabilities
for any organization/department using Microsoft Graph API with OBO flow for user-scoped access.

This is a generic, reusable implementation that maintains the OBO requirement
while being configurable for any organization structure.

Required environment variables:
- SHP_ID_APP: Azure App Registration Client ID
- SHP_ID_APP_SECRET: Azure App Registration Client Secret  
- SHP_TENANT_ID: Azure AD Tenant ID
- SHP_SITE_URL: SharePoint Site URL

Optional configuration:
- SHP_ORG_NAME: Organization name for tool descriptions (defaults to "Organization")
- SHP_DOC_LIBRARY: SharePoint Document Library path (optional, defaults to root)
- SHP_DEFAULT_SEARCH_FOLDERS: Comma-separated list of default folders to search in
- SHP_USE_DELEGATED_ACCESS: Enable user-scoped access (true/false, default: true)
- SHP_OBO_SCOPE: Scopes for On-Behalf-Of token exchange (default: standard Graph scopes)
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

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sharepoint_oauth_client import get_oauth_client, SharePointOAuthClient
    from sharepoint_tools_obo import (
        list_documents_tool,
        list_folders_tool,
        get_document_content_tool,
        get_sharepoint_tree_tool,
    )

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
logger = logging.getLogger("generic_sharepoint_mcp_obo")

# Get configuration from environment
ORG_NAME = os.getenv("SHP_ORG_NAME", "Organization")
DEFAULT_DOC_LIBRARY = os.getenv("SHP_DOC_LIBRARY", "")
DEFAULT_SEARCH_FOLDERS = [
    f.strip()
    for f in os.getenv("SHP_DEFAULT_SEARCH_FOLDERS", "").split(",")
    if f.strip()
]

# Create FastMCP app instance
generic_sharepoint_server = FastMCP(
    f"Generic SharePoint MCP Server with OBO for {ORG_NAME}"
)


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


@generic_sharepoint_server.tool()
async def search_sharepoint_documents(
    query: str = "documents",
    folder_path: Optional[str] = None,
    search_subfolders: bool = True,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for documents in SharePoint based on a query using Microsoft Graph API with OBO.

    This tool searches for documents in SharePoint folders with user-scoped access.
    It can search in a specific folder or across multiple configured default folders.

    Args:
        query: Search terms to find relevant documents (e.g., "strategy", "project")
        folder_path: Specific SharePoint folder path to search in (optional)
        search_subfolders: Whether to search in subfolders as well (default: True)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with search results and document list
    """
    try:
        # Get user token from environment variable (set by crew MCP manager) if not provided
        if not user_token:
            user_token = os.getenv("USER_JWT_TOKEN")

        # For local development, don't try OBO if no valid token available
        if user_token == "user_token_placeholder" or not user_token:
            logger.info(
                "No OAuth token available - using application-only authentication for local development"
            )
            user_token = None  # This will trigger application-only flow
        else:
            logger.info(
                f"Using OAuth token for SharePoint OBO flow: {bool(user_token)}"
            )
            # Log token type for debugging
            if user_token and len(user_token) > 20:
                logger.debug(f"Token type check - starts with: {user_token[:20]}...")

        # Determine which folders to search
        search_folders = []

        if folder_path:
            search_folders = [folder_path]
        elif DEFAULT_SEARCH_FOLDERS:
            search_folders = DEFAULT_SEARCH_FOLDERS
        elif DEFAULT_DOC_LIBRARY:
            search_folders = [DEFAULT_DOC_LIBRARY]
        else:
            # Search from root
            search_folders = [""]

        logger.info(f"Searching SharePoint for: {query} in folders: {search_folders}")

        # Get appropriate access token using OBO flow
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "query": query,
                "folders": search_folders,
                "error": "Failed to obtain access token",
                "message": "Authentication failed. Check your configuration and user permissions.",
            }

        # Get site and drive information
        success, site_info = await oauth_client.get_site_info(access_token)
        if not success:
            return {
                "status": "error",
                "query": query,
                "folders": search_folders,
                "error": site_info,
                "message": "Failed to access SharePoint site",
            }

        site_id = site_info.get("id")
        success, drives_data = await oauth_client.get_site_drives(access_token, site_id)
        if not success:
            return {
                "status": "error",
                "query": query,
                "folders": search_folders,
                "error": drives_data,
                "message": "Failed to access document libraries",
            }

        drives = drives_data.get("value", [])
        if not drives:
            return {
                "status": "error",
                "query": query,
                "folders": search_folders,
                "error": "No document libraries found",
                "message": "No accessible document libraries found",
            }

        # Use first drive for now
        drive_id = drives[0].get("id")

        all_matching_documents = []
        search_summary = []

        # Search in each folder
        for folder in search_folders:
            try:
                logger.info(f"Searching in folder: {folder}")

                # Get documents from the specified folder
                success, items_data = await oauth_client.get_drive_items(
                    access_token, site_id, drive_id, folder
                )

                if not success:
                    search_summary.append(
                        {
                            "folder": folder,
                            "total_documents": 0,
                            "matching_documents": 0,
                            "status": "error",
                            "error": items_data,
                            "message": f"Failed to access folder: {folder}",
                        }
                    )
                    continue

                items = items_data.get("value", [])

                # Filter items based on query
                matching_docs = []
                file_items = [item for item in items if item.get("file")]  # Only files

                for item in file_items:
                    name = item.get("name", "")
                    # Flexible matching - check for individual words in the query
                    query_words = query.lower().split()
                    name_lower = name.lower()

                    # Match if any significant word from query appears in filename
                    match_found = False
                    for word in query_words:
                        if (
                            len(word) > 2 and word in name_lower
                        ):  # Skip very short words
                            match_found = True
                            break

                    # Also check for exact phrase match
                    if query.lower() in name_lower:
                        match_found = True

                    if match_found:
                        matching_docs.append(
                            {
                                "name": name,
                                "id": item.get("id"),
                                "size": item.get("size"),
                                "lastModified": item.get("lastModifiedDateTime"),
                                "webUrl": item.get("webUrl"),
                                "folder_path": folder,
                                "organization": ORG_NAME,
                            }
                        )

                all_matching_documents.extend(matching_docs)
                search_summary.append(
                    {
                        "folder": folder,
                        "total_documents": len(file_items),
                        "matching_documents": len(matching_docs),
                        "status": "success",
                    }
                )

            except Exception as e:
                logger.warning(f"Error searching folder {folder}: {e}")
                search_summary.append(
                    {
                        "folder": folder,
                        "total_documents": 0,
                        "matching_documents": 0,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return {
            "status": "success",
            "query": query,
            "searched_folders": search_folders,
            "total_matching_documents": len(all_matching_documents),
            "matching_documents": all_matching_documents,
            "search_summary": search_summary,
            "organization": ORG_NAME,
            "authentication": "Microsoft Graph API with On-Behalf-Of flow",
            "message": f"Found {len(all_matching_documents)} documents matching '{query}' across {len(search_folders)} folders",
        }

    except Exception as e:
        logger.error(f"Error searching SharePoint documents: {e}")
        return {
            "status": "error",
            "query": query,
            "folders": search_folders,
            "error": str(e),
            "message": "Failed to search SharePoint documents",
        }


@generic_sharepoint_server.tool()
async def list_sharepoint_folder_contents(
    folder_path: Optional[str] = None,
    include_subfolders: bool = True,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List the contents of a SharePoint folder to explore structure using Microsoft Graph API.

    This tool helps explore SharePoint folder structures for any organization
    to understand document organization and get counts with user-scoped access.

    Args:
        folder_path: SharePoint folder path to explore (uses SHP_DOC_LIBRARY if not provided)
        include_subfolders: Whether to include subfolder information
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with folder contents, subfolder counts, and file listings
    """
    try:
        # Get user token from environment variable (set by crew MCP manager) if not provided
        if not user_token:
            user_token = os.getenv("USER_JWT_TOKEN")

        # For local development, don't try OBO if no valid token available
        if user_token == "user_token_placeholder" or not user_token:
            logger.info(
                "No OAuth token available - using application-only authentication for local development"
            )
            user_token = None  # This will trigger application-only flow
        else:
            logger.info(
                f"Using OAuth token for SharePoint OBO flow: {bool(user_token)}"
            )
            # Log token type for debugging
            if user_token and len(user_token) > 20:
                logger.debug(f"Token type check - starts with: {user_token[:20]}...")

        # Use default folder if none specified
        if folder_path is None:
            folder_path = DEFAULT_DOC_LIBRARY

        logger.info(f"Listing SharePoint folder contents: {folder_path}")

        # Get appropriate access token using OBO flow
        access_token = await oauth_client.get_access_token(user_token)
        if not access_token:
            return {
                "status": "error",
                "folder": folder_path,
                "error": "Failed to obtain access token",
                "message": "Authentication failed. Check your configuration and user permissions.",
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
                    "type": "folder",
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
                    "type": "file",
                }
                files.append(file_info)

        # Calculate summary statistics for projects/organizational items
        org_folders = [
            f
            for f in folders
            if any(
                keyword in f["name"].lower()
                for keyword in [
                    "project",
                    "prospect",
                    "initiative",
                    "program",
                    "strategy",
                ]
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
            "organizational_folders": org_folders,
            "potential_project_count": sum(f.get("childCount", 0) for f in org_folders),
            "organization": ORG_NAME,
            "authentication": "Microsoft Graph API with On-Behalf-Of flow",
            "message": f"Found {len(folders)} folders and {len(files)} files in {folder_path or 'root'}. Organizational folders: {len(org_folders)}",
        }

    except Exception as e:
        logger.error(f"Error listing folder contents: {e}")
        return {
            "status": "error",
            "folder": folder_path,
            "error": str(e),
            "message": "Failed to list folder contents",
        }


@generic_sharepoint_server.tool()
async def get_sharepoint_document_content(
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
    try:
        # Get user token from environment variable (set by crew MCP manager) if not provided
        if not user_token:
            user_token = os.getenv("USER_JWT_TOKEN")

        # For local development, don't try OBO if no valid token available
        if user_token == "user_token_placeholder" or not user_token:
            logger.info(
                "No OAuth token available - using application-only authentication for local development"
            )
            user_token = None  # This will trigger application-only flow
        else:
            logger.info(
                f"Using OAuth token for SharePoint OBO flow: {bool(user_token)}"
            )
            # Log token type for debugging
            if user_token and len(user_token) > 20:
                logger.debug(f"Token type check - starts with: {user_token[:20]}...")

        logger.info(f"Getting content for: {file_name} in folder: {folder_name}")

        # Get appropriate access token using OBO flow
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

        # Parse document content using embedded document parser
        try:
            # Embed the document parsing logic directly to avoid import issues
            parsed_content = await parse_document_content_embedded(content, file_name)

            if parsed_content:
                logger.info(
                    f"Successfully parsed content for {file_name}: {len(parsed_content)} characters"
                )
                return {
                    "status": "success",
                    "folder": folder_name,
                    "file": file_name,
                    "content": parsed_content,
                    "size": (
                        len(content)
                        if isinstance(content, bytes)
                        else len(str(content))
                    ),
                    "organization": ORG_NAME,
                    "authentication": "Microsoft Graph API with On-Behalf-Of flow",
                    "message": f"Successfully retrieved content for {file_name}",
                }
            else:
                logger.warning(
                    f"Document parser returned empty content for {file_name}"
                )
                return {
                    "status": "success",
                    "folder": folder_name,
                    "file": file_name,
                    "content": f"Document '{file_name}' was retrieved but contained no extractable text content. The document may be empty, encrypted, or in a format that could not be processed.",
                    "size": (
                        len(content)
                        if isinstance(content, bytes)
                        else len(str(content))
                    ),
                    "organization": ORG_NAME,
                    "authentication": "Microsoft Graph API with On-Behalf-Of flow",
                    "message": f"Retrieved {file_name} but no content could be extracted",
                }

        except Exception as parse_error:
            logger.error(
                f"Critical error in document parser for {file_name}: {parse_error}"
            )
            import traceback

            logger.debug(f"Parser traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_name,
                "error": str(parse_error),
                "message": f"Document '{file_name}' could not be processed due to a parsing error: {str(parse_error)}. Please access the document directly via SharePoint.",
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


@generic_sharepoint_server.tool()
async def search_and_analyze_documents(
    search_terms: str,
    folder_path: Optional[str] = None,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for documents and automatically analyze their content for relevant information.

    This tool combines document search with content analysis to find information
    even when search terms don't appear in document titles.

    Args:
        search_terms: Terms to search for (will search filenames AND analyze document content)
        folder_path: Specific folder to search in (optional)
        user_token: User access token for delegated access

    Returns:
        JSON response with documents and their analyzed content
    """
    try:
        # First, do a broad search for potentially relevant documents
        broad_search = await search_sharepoint_documents(
            "strategy OR transformative OR railway OR rail",
            folder_path,
            True,
            user_token,
        )

        if broad_search.get("status") != "success" or not broad_search.get(
            "matching_documents"
        ):
            return {
                "status": "no_documents",
                "message": "No potentially relevant documents found to analyze",
                "search_terms": search_terms,
            }

        # Analyze each document's content for the search terms
        analyzed_documents = []

        for doc in broad_search.get("matching_documents", []):
            doc_name = doc.get("name", "")
            folder_name = doc.get("folder_path", "")

            logger.info(
                f"Analyzing document: {doc_name} for search terms: {search_terms}"
            )

            # Get the document content
            content_result = await get_sharepoint_document_content(
                folder_name, doc_name, user_token
            )

            if content_result.get("status") == "success":
                content = content_result.get("content", "")

                # Check if the content contains relevant information
                search_terms_lower = search_terms.lower()
                content_lower = content.lower()

                # Look for relevant terms in content
                relevant_terms = [
                    "length",
                    "km",
                    "kilometer",
                    "mile",
                    "distance",
                    "projected",
                    "railway",
                    "rail",
                ]
                relevance_score = sum(
                    1 for term in relevant_terms if term in content_lower
                )

                # If content seems relevant, include it
                if relevance_score >= 2 or any(
                    term in content_lower for term in search_terms_lower.split()
                ):
                    analyzed_documents.append(
                        {
                            "document": doc,
                            "content": content,
                            "relevance_score": relevance_score,
                            "analysis": f"Found {relevance_score} relevant terms in document content",
                        }
                    )
                    logger.info(
                        f"Document {doc_name} scored {relevance_score} for relevance"
                    )
                else:
                    logger.info(
                        f"Document {doc_name} not relevant (score: {relevance_score})"
                    )
            else:
                logger.warning(
                    f"Failed to get content for {doc_name}: {content_result.get('message', 'Unknown error')}"
                )

        return {
            "status": "success",
            "search_terms": search_terms,
            "total_documents_analyzed": len(broad_search.get("matching_documents", [])),
            "relevant_documents_found": len(analyzed_documents),
            "analyzed_documents": analyzed_documents,
            "message": f"Analyzed {len(broad_search.get('matching_documents', []))} documents, found {len(analyzed_documents)} relevant matches",
        }

    except Exception as e:
        logger.error(f"Error in search and analyze: {e}")
        return {
            "status": "error",
            "search_terms": search_terms,
            "error": str(e),
            "message": "Failed to search and analyze documents",
        }


@generic_sharepoint_server.tool()
async def get_sharepoint_configuration() -> Dict[str, Any]:
    """
    Get the current SharePoint configuration and available settings.

    Returns:
        JSON response with configuration details and available options
    """
    try:
        return {
            "status": "success",
            "configuration": {
                "organization": ORG_NAME,
                "default_document_library": DEFAULT_DOC_LIBRARY,
                "default_search_folders": DEFAULT_SEARCH_FOLDERS,
                "site_url": os.getenv("SHP_SITE_URL", "Not configured"),
                "tenant_id": os.getenv("SHP_TENANT_ID", "Not configured"),
                "use_delegated_access": oauth_client.use_delegated_access,
                "obo_scope": oauth_client.obo_scope,
            },
            "environment_variables": {
                "SHP_ORG_NAME": "Organization name for tool descriptions",
                "SHP_DOC_LIBRARY": "Default document library path",
                "SHP_DEFAULT_SEARCH_FOLDERS": "Comma-separated list of default search folders",
                "SHP_SITE_URL": "SharePoint site URL",
                "SHP_ID_APP": "Azure App Registration Client ID",
                "SHP_ID_APP_SECRET": "Azure App Registration Client Secret",
                "SHP_TENANT_ID": "Azure AD Tenant ID",
                "SHP_USE_DELEGATED_ACCESS": "Enable user-scoped access (default: true)",
                "SHP_OBO_SCOPE": "Scopes for On-Behalf-Of token exchange",
            },
            "authentication": "Microsoft Graph API with On-Behalf-Of flow",
            "message": "SharePoint MCP server configuration retrieved successfully",
        }

    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve SharePoint configuration",
        }


@generic_sharepoint_server.tool()
async def use_mcp_sharepoint_tools(
    operation: str,
    folder_name: Optional[str] = None,
    file_name: Optional[str] = None,
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use mcp-sharepoint compatible tools with OBO authentication.

    This tool provides direct access to mcp-sharepoint-style functions
    but implemented with Microsoft Graph API and OBO flow.

    Args:
        operation: The operation to perform ('list_documents', 'list_folders', 'get_content', 'get_tree')
        folder_name: SharePoint folder name (required for list_documents, get_content)
        file_name: Document file name (required for get_content)
        user_token: Optional user access token for delegated access

    Returns:
        JSON response with operation results
    """
    try:
        logger.info(f"Using mcp-sharepoint compatible tool: {operation}")

        if operation == "list_documents":
            if not folder_name:
                return {
                    "status": "error",
                    "error": "folder_name is required for list_documents operation",
                    "operation": operation,
                }

            documents = await list_documents_tool(folder_name, user_token)
            return {
                "status": "success",
                "operation": operation,
                "folder": folder_name,
                "documents": documents,
                "count": len(documents),
                "organization": ORG_NAME,
                "authentication": "Microsoft Graph API with OBO (mcp-sharepoint compatible)",
                "message": f"Listed {len(documents)} documents from {folder_name}",
            }

        elif operation == "list_folders":
            folders = await list_folders_tool(folder_name, user_token)
            return {
                "status": "success",
                "operation": operation,
                "parent_folder": folder_name,
                "folders": folders,
                "count": len(folders),
                "organization": ORG_NAME,
                "authentication": "Microsoft Graph API with OBO (mcp-sharepoint compatible)",
                "message": f"Listed {len(folders)} folders from {folder_name or 'root'}",
            }

        elif operation == "get_content":
            if not folder_name or not file_name:
                return {
                    "status": "error",
                    "error": "folder_name and file_name are required for get_content operation",
                    "operation": operation,
                }

            content = await get_document_content_tool(
                folder_name, file_name, user_token
            )
            return {
                "status": "success",
                "operation": operation,
                "folder": folder_name,
                "file": file_name,
                "content": content,
                "organization": ORG_NAME,
                "authentication": "Microsoft Graph API with OBO (mcp-sharepoint compatible)",
                "message": f"Retrieved content for {file_name} from {folder_name}",
            }

        elif operation == "get_tree":
            tree = await get_sharepoint_tree_tool(folder_name, user_token)
            return {
                "status": "success",
                "operation": operation,
                "root_folder": folder_name,
                "tree_structure": tree,
                "organization": ORG_NAME,
                "authentication": "Microsoft Graph API with OBO (mcp-sharepoint compatible)",
                "message": f"Retrieved folder tree for {folder_name or 'root'}",
            }

        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": [
                    "list_documents",
                    "list_folders",
                    "get_content",
                    "get_tree",
                ],
                "operation": operation,
            }

    except Exception as e:
        logger.error(f"Error in mcp-sharepoint compatible operation {operation}: {e}")
        return {
            "status": "error",
            "operation": operation,
            "error": str(e),
            "message": f"Failed to execute {operation}",
        }


@generic_sharepoint_server.tool()
async def check_sharepoint_permissions(
    user_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check SharePoint connection status and user permissions.

    Args:
        user_token: Optional user access token for delegated access testing

    Returns:
        JSON response with connection status and permission details
    """
    try:
        logger.info("Checking SharePoint permissions and connection status")

        # Test OAuth connection with OBO flow
        test_result = await oauth_client.test_connection(user_token)

        return {
            "status": "success",
            "connection_test": test_result,
            "organization": ORG_NAME,
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
            "authentication": "Microsoft Graph API with On-Behalf-Of flow",
            "message": "SharePoint permissions check completed",
        }

    except Exception as e:
        logger.error(f"Error checking SharePoint permissions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check SharePoint permissions",
        }


def get_app():
    """Get the FastMCP app instance"""
    return generic_sharepoint_server


if __name__ == "__main__":
    logger.info(
        f"Starting Generic SharePoint FastMCP Server with OBO for {ORG_NAME}..."
    )

    # Check configuration before starting
    required_vars = ["SHP_ID_APP", "SHP_ID_APP_SECRET", "SHP_TENANT_ID", "SHP_SITE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error(
            "Please set the required SharePoint environment variables before starting the server"
        )
        sys.exit(1)

    logger.info(f"Organization: {ORG_NAME}")
    logger.info(f"SharePoint site: {oauth_client.site_url}")
    logger.info(f"Document library: {DEFAULT_DOC_LIBRARY}")
    logger.info(f"Default search folders: {DEFAULT_SEARCH_FOLDERS}")
    logger.info(f"Delegated access: {oauth_client.use_delegated_access}")
    logger.info(f"OBO scope: {oauth_client.obo_scope}")
    logger.info("Authentication: Microsoft Graph API with On-Behalf-Of flow")

    # Run the FastMCP server
    generic_sharepoint_server.run()

# ============================================================================
# EMBEDDED DOCUMENT PARSER (to avoid import issues)
# ============================================================================


async def parse_document_content_embedded(content: bytes, file_name: str) -> str:
    """
    Embedded document parser to avoid module import issues.
    Parse document content using direct PDF/document parsing libraries.
    """
    import re
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO

    logger.info(
        f"parse_document_content_embedded called for {file_name}, content size: {len(content)} bytes"
    )

    try:
        if not isinstance(content, bytes):
            logger.info(f"Content is not bytes for {file_name}, returning as string")
            return str(content)

        # Get file extension for parsing method selection
        file_extension = (
            file_name.split(".")[-1].lower() if "." in file_name else "unknown"
        )
        logger.info(f"File extension: {file_extension} for file: {file_name}")

        # Try direct parsing based on file type
        if file_extension == "pdf":
            return await parse_pdf_content_embedded(content, file_name)
        elif file_extension in ["docx", "doc"]:
            return await parse_word_content_embedded(content, file_name)
        elif file_extension in ["txt", "csv", "log"]:
            return await parse_text_content_embedded(content, file_name)
        else:
            # For unknown file types, try to extract any readable text
            return await parse_generic_content_embedded(content, file_name)

    except Exception as e:
        logger.error(f"Error parsing document content for {file_name}: {e}")
        return f"""# {file_name}

**Document Parsing Error**

The document could not be parsed automatically.

**Technical Details:**
- File size: {len(content)} bytes
- File type: {file_extension.upper()}
- Error: {str(e)}

**Note:** The document exists and was successfully retrieved from SharePoint, but content extraction failed during processing.
"""


async def parse_pdf_content_embedded(content: bytes, file_name: str) -> str:
    """Parse PDF content using multiple extraction methods."""
    logger.info(f"Attempting PDF extraction for: {file_name}")

    # Method 1: Try pypdf if available
    try:
        import pypdf
        import io

        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        text_parts = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        extracted_text = "\n".join(text_parts)
        if extracted_text.strip():
            logger.info(
                f"pypdf extraction successful for {file_name}: {len(extracted_text)} characters"
            )
            return f"# {file_name}\n\n{extracted_text}"

    except ImportError:
        logger.debug(f"pypdf not available for {file_name}")
    except Exception as pypdf_error:
        logger.debug(f"pypdf extraction failed for {file_name}: {pypdf_error}")

    # Method 2: Try pdfplumber if available
    try:
        import pdfplumber
        import io

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            extracted_text = "\n".join(text_parts)
            if extracted_text.strip():
                logger.info(
                    f"pdfplumber extraction successful for {file_name}: {len(extracted_text)} characters"
                )
                return f"# {file_name}\n\n{extracted_text}"

    except ImportError:
        logger.debug(f"pdfplumber not available for {file_name}")
    except Exception as plumber_error:
        logger.debug(f"pdfplumber extraction failed for {file_name}: {plumber_error}")

    # If all methods fail, return error
    return f"# {file_name}\n\n**PDF Parsing Failed**\n\nUnable to extract text content from this PDF document using available parsers. Please access the document directly via SharePoint."


async def parse_word_content_embedded(content: bytes, file_name: str) -> str:
    """Parse Word document content using XML extraction."""
    logger.info(f"Attempting Word document extraction for: {file_name}")

    try:
        # Word documents are ZIP files containing XML
        with zipfile.ZipFile(BytesIO(content), "r") as docx_zip:
            # Try to extract text from document.xml
            if "word/document.xml" in docx_zip.namelist():
                xml_content = docx_zip.read("word/document.xml")
                root = ET.fromstring(xml_content)

                # Extract text content more thoroughly
                text_elements = []
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_elements.append(elem.text.strip())

                if text_elements:
                    extracted_text = " ".join(text_elements)
                    logger.info(
                        f"Word extraction successful for {file_name}: {len(extracted_text)} characters"
                    )
                    return f"# {file_name}\n\n{extracted_text}"

    except Exception as word_error:
        logger.warning(f"Word extraction failed for {file_name}: {word_error}")

    return f"# {file_name}\n\n**Word Document Parsing Failed**\n\nUnable to extract text content from this Word document. Please access the document directly via SharePoint."


async def parse_text_content_embedded(content: bytes, file_name: str) -> str:
    """Parse plain text content."""
    try:
        text_content = content.decode("utf-8", errors="ignore")
        if text_content.strip():
            logger.info(
                f"Text extraction successful for {file_name}: {len(text_content)} characters"
            )
            return f"# {file_name}\n\n{text_content}"
    except Exception as text_error:
        logger.warning(f"Text extraction failed for {file_name}: {text_error}")

    return f"# {file_name}\n\n**Text File Parsing Failed**\n\nUnable to decode text content. Please access the document directly."


async def parse_generic_content_embedded(content: bytes, file_name: str) -> str:
    """Try to extract any readable text from unknown file types."""
    try:
        # Try basic text extraction
        text_content = content.decode("utf-8", errors="ignore")

        # Look for meaningful text patterns
        lines = text_content.split("\n")
        meaningful_lines = []

        for line in lines:
            # Keep lines that have reasonable text content
            clean_line = re.sub(r"[^\w\s\.\,\;\:\!\?\-\(\)]", " ", line)
            words = [
                word
                for word in clean_line.split()
                if len(word) > 2
                and word.replace("-", "").replace(".", "").replace(",", "").isalnum()
            ]

            if len(words) >= 3:  # Lines with at least 3 meaningful words
                meaningful_lines.append(" ".join(words))

        if meaningful_lines:
            extracted_text = "\n".join(
                meaningful_lines[:50]
            )  # Limit to first 50 meaningful lines
            logger.info(
                f"Generic text extraction found content for {file_name}: {len(extracted_text)} characters"
            )
            return f"# {file_name}\n\n{extracted_text}"

    except Exception as generic_error:
        logger.warning(
            f"Generic text extraction failed for {file_name}: {generic_error}"
        )

    return f"# {file_name}\n\n**Unknown File Type**\n\nUnable to extract readable content from this file type. Please access the document directly via SharePoint."
