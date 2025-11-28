#!/usr/bin/env python3
"""
MPO-Specific SharePoint MCP Configuration with OBO Flow

This file provides MPO-specific configuration for the generic SharePoint MCP server
with Microsoft Graph API and On-Behalf-Of flow support.

This approach maintains OBO requirements while providing organization-specific optimizations.
"""
import os
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the generic SharePoint server with OBO support
from generic_sharepoint_server_obo import generic_sharepoint_server

# MPO-specific configuration
MPO_CONFIG = {
    "ORG_NAME": "Major Projects Office (MPO)",
    "DOC_LIBRARY": "Major Projects Office (MPO)",
    "DEFAULT_SEARCH_FOLDERS": [
        "Major Projects Office (MPO)",
        "Major Projects Office (MPO)/Communications",
        "Major Projects Office (MPO)/3 - Transformative Strategies",
        "Major Projects Office (MPO)/2 - Projects",
        "Major Projects Office (MPO)/1 - Prospects",
    ],
    "COMMON_SUBFOLDERS": [
        "Communications",
        "Projects",
        "Prospects",
        "Transformative Strategies",
    ],
}

# Set MPO-specific environment variables if not already set
if not os.getenv("SHP_ORG_NAME"):
    os.environ["SHP_ORG_NAME"] = MPO_CONFIG["ORG_NAME"]

if not os.getenv("SHP_DOC_LIBRARY"):
    os.environ["SHP_DOC_LIBRARY"] = MPO_CONFIG["DOC_LIBRARY"]

if not os.getenv("SHP_DEFAULT_SEARCH_FOLDERS"):
    os.environ["SHP_DEFAULT_SEARCH_FOLDERS"] = ",".join(
        MPO_CONFIG["DEFAULT_SEARCH_FOLDERS"]
    )

# Don't create confusing MPO-specific tools - the generic server handles everything
# The configuration above is sufficient for MPO-specific behavior


def get_mpo_app():
    """Get the MPO-configured SharePoint MCP app"""
    return generic_sharepoint_server


if __name__ == "__main__":
    print("Starting MPO SharePoint MCP Server...")
    print(f"Organization: {MPO_CONFIG['ORG_NAME']}")
    print(f"Document Library: {MPO_CONFIG['DOC_LIBRARY']}")
    print(f"Search Folders: {len(MPO_CONFIG['DEFAULT_SEARCH_FOLDERS'])}")

    # Run the server with MPO configuration
    generic_sharepoint_server.run()
