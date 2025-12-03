#!/usr/bin/env python3
"""
MPO (Major Projects Office) SharePoint MCP Server

This server provides SharePoint document search and retrieval capabilities
specifically for the Major Projects Office (MPO) using the multi-department
generic SharePoint server framework.

Environment variables required:
- Global: SHP_USE_DELEGATED_ACCESS, SHP_OBO_SCOPE
- MPO-specific: MPO_SHP_ID_APP, MPO_SHP_ID_APP_SECRET, MPO_SHP_TENANT_ID,
  MPO_SHP_SITE_URL, MPO_SHP_ORG_NAME, MPO_SHP_DOC_LIBRARY, MPO_SHP_DEFAULT_SEARCH_FOLDERS
"""
import logging
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the multi-department generic server components
from generic_sharepoint_server_multi_dept import initialize_department_server, mcp


def setup_mpo_server():
    """Initialize the MPO SharePoint server configuration"""
    try:
        logging.info("Setting up MPO SharePoint MCP Server")

        # Initialize server for MPO department
        success = initialize_department_server("MPO")
        if not success:
            logging.error("Failed to initialize MPO SharePoint server")
            return False

        logging.info("MPO SharePoint MCP Server configuration complete")
        return True

    except Exception as e:
        logging.error(f"Error setting up MPO SharePoint server: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - MPO-SharePoint - %(levelname)s - %(message)s",
    )

    # Setup the server configuration
    if setup_mpo_server():
        logging.info("Starting MPO SharePoint MCP Server with stdio transport")
        # Run the server directly like other FastMCP servers
        mcp.run()
    else:
        logging.error("Failed to setup MPO SharePoint server")
        sys.exit(1)
