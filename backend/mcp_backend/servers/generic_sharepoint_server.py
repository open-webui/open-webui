#!/usr/bin/env python3
"""
SharePoint MCP Server

This server provides SharePoint document search and retrieval capabilities using the
multi-department generic SharePoint server framework.

Environment variables required for {DEPT_UPPER}:
- Global: SHP_USE_DELEGATED_ACCESS, SHP_OBO_SCOPE (shared across all departments)
- Department-specific:
  - {DEPT_UPPER}_SHP_ID_APP: Azure AD application client ID
  - {DEPT_UPPER}_SHP_ID_APP_SECRET: Azure AD application client secret
  - {DEPT_UPPER}_SHP_TENANT_ID: Azure AD tenant ID
  - {DEPT_UPPER}_SHP_SITE_URL: SharePoint site URL
  - {DEPT_UPPER}_SHP_ORG_NAME: Department name for tool descriptions
  - {DEPT_UPPER}_SHP_DOC_LIBRARY: Default document library path (optional)
  - {DEPT_UPPER}_SHP_DEFAULT_SEARCH_FOLDERS: Default search folders (optional)

Example for Finance Department (DEPT_UPPER = FIN):
  - FIN_SHP_ID_APP=''
  - FIN_SHP_ID_APP_SECRET=''
  - FIN_SHP_TENANT_ID=''
  - FIN_SHP_SITE_URL=''
  - FIN_SHP_ORG_NAME='Finance Department'
  - FIN_SHP_DOC_LIBRARY='Finance'
  - FIN_SHP_DEFAULT_SEARCH_FOLDERS='Finance/Reports,Finance/Policies,Finance/Budgets'
"""

import logging
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the multi-department generic server components
from generic_sharepoint_server_multi_dept import initialize_department_server, mcp


def setup_server(dept: str):
    f"""Initialize the {dept} SharePoint server configuration"""
    try:
        logging.info(f"Setting up the {dept} SharePoint MCP Server")

        # Initialize server for MPO department
        success = initialize_department_server(dept)
        if not success:
            logging.error(
                f"Failed to initialize {dept} SharePoint server - will continue with no tools"
            )
            logging.warning("Server will run but tools will not be available")
            # Don't return False - let the server run even if init fails
            # This allows the process to stay alive for debugging
            return True  # Changed from False

        logging.info(f"{dept} SharePoint MCP Server configuration complete")
        return True

    except Exception as e:
        logging.error(f"Error setting up {dept} SharePoint server: {e}", exc_info=True)
        logging.warning("Server will run but tools will not be available")
        # Don't fail - let the server run for debugging
        return True  # Changed from False


if __name__ == "__main__":
    if len(sys.argv) < 1:
        logging.error(
            "No argument passed for setting up department MCP Sharepoint server."
        )
        sys.exit(1)
    else:
        DEPT = sys.argv[1]

    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s - {DEPT}-SharePoint - %(levelname)s - %(message)s",
    )

    # Setup the server configuration
    if setup_server(dept=DEPT):
        logging.info(f"Starting {DEPT} SharePoint MCP Server with stdio transport")
        # Run the server directly like other FastMCP servers
        mcp.run()
    else:
        logging.error(f"Failed to setup {DEPT} SharePoint server")
        sys.exit(1)
