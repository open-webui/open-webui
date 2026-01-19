#!/usr/bin/env python3
"""
TEMPLATE: Department SharePoint MCP Server

This is a template for creating department-specific SharePoint MCP servers.
To onboard a new department:

1. Copy this file and rename it to: {DEPT_LOWER}_sharepoint_server.py
2. Replace {DEPT_UPPER} with the department's prefix (e.g., FIN, IT, HR)
3. Replace {DEPT_NAME} with the department's full name (e.g., Finance Department)
4. Add the department's environment variables to .env.example and .env
5. Update mcp_manager.py to include the new server

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

import asyncio
import logging
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the multi-department generic server
from generic_sharepoint_server_multi_dept import main as run_generic_server


async def main():
    """Main function to run the {DEPT_NAME} SharePoint MCP server"""
    try:
        logging.info("Starting {DEPT_NAME} SharePoint MCP Server")
        # Initialize the generic server with {DEPT_UPPER} department prefix
        await run_generic_server(department_prefix="{DEPT_UPPER}")

    except Exception as e:
        logging.error(f"Error starting {DEPT_NAME} SharePoint server: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - {DEPT_UPPER}-SharePoint - %(levelname)s - %(message)s",
    )

    asyncio.run(main())


# ONBOARDING CHECKLIST FOR NEW DEPARTMENT:
#
# □ 1. Copy this template and rename file to: {dept_lower}_sharepoint_server.py
# □ 2. Replace all {DEPT_UPPER} placeholders with department prefix (e.g., FIN, IT, HR)
# □ 3. Replace all {DEPT_NAME} placeholders with full department name
# □ 4. Replace all {dept_lower} placeholders with lowercase department prefix
# □ 5. Add department environment variables to .env.example:
#      - {DEPT_UPPER}_SHP_ID_APP=''
#      - {DEPT_UPPER}_SHP_ID_APP_SECRET=''
#      - {DEPT_UPPER}_SHP_TENANT_ID=''
#      - {DEPT_UPPER}_SHP_SITE_URL=''
#      - {DEPT_UPPER}_SHP_ORG_NAME='Department Name'
#      - {DEPT_UPPER}_SHP_DOC_LIBRARY='' (optional)
#      - {DEPT_UPPER}_SHP_DEFAULT_SEARCH_FOLDERS='' (optional)
# □ 6. Add department environment variables to your local .env file
# □ 7. Update mcp_backend/management/mcp_manager.py to include new server:
#      Add a new section in setup_internal_servers() method similar to MPO
# □ 8. Test the new department server locally
# □ 9. Deploy and configure Azure AD app registration with proper permissions
# □ 10. Add to production environment variables via Terraform/Azure KeyVault
