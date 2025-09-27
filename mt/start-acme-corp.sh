#!/bin/bash
# ACME Corp Open WebUI Instance

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Call the template script from the same directory
${SCRIPT_DIR}/start-template.sh acme-corp 8081 acme.yourdomain.com