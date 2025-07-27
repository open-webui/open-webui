#!/usr/bin/env python3
"""
generate_client_env.py

Clean Architecture implementation for generating .env configuration files
for mAI client Docker instances using OpenRouter Provisioning API.

This is the new refactored version that replaces the monolithic 740-line class
with a proper Clean Architecture pattern implementation.

Usage:
    python generate_client_env.py
    python generate_client_env.py --init-database
    python generate_client_env.py --production

Requirements:
    - OpenRouter Provisioning API key
    - Network connectivity to OpenRouter API
    - Write permissions for .env file generation
"""

import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_client_env.main import main

if __name__ == "__main__":
    sys.exit(main())