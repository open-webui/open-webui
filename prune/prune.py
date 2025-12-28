#!/usr/bin/env python3
"""
Open WebUI Prune - Unified CLI Entry Point

This is the main entry point that provides both interactive and non-interactive
CLI modes for pruning Open WebUI data.

Usage:
    # Interactive mode (default if no arguments)
    python prune.py

    # Non-interactive mode with arguments
    python prune.py --days 60 --execute

    # Force interactive mode
    python prune.py --interactive

    # Show help
    python prune.py --help
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))


def main():
    """Main entry point - route to interactive or non-interactive mode."""
    # Quick check for interactive mode
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--interactive', '-i']):
        # No arguments or just --interactive = run interactive mode
        try:
            from prune_cli_interactive import main as interactive_main
            return interactive_main()
        except ImportError as e:
            print(f"ERROR: Cannot run interactive mode: {e}")
            print("\nInteractive mode requires the 'rich' library.")
            print("Install it with: pip install rich")
            print("\nOr use non-interactive mode with command-line arguments:")
            print("  python prune.py --help")
            return 1

    # Parse just enough to check if --help is requested
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return 0

    # Has arguments = run non-interactive mode
    try:
        from standalone_prune import main as standalone_main
        return standalone_main()
    except ImportError as e:
        print(f"ERROR: Cannot run prune script: {e}")
        print("\nMake sure:")
        print("  1. You're running from the Open WebUI directory")
        print("  2. Open WebUI dependencies are installed")
        print("  3. PYTHONPATH is set correctly")
        return 1


def show_help():
    """Show help message that covers both modes."""
    help_text = """
Open WebUI Prune Tool - Database Cleanup Utility

This tool provides two modes of operation:

═══════════════════════════════════════════════════════════════════════════
INTERACTIVE MODE (Recommended for Manual Use)
═══════════════════════════════════════════════════════════════════════════

Launch with no arguments for a beautiful interactive UI:

    python prune.py
    python prune.py --interactive

Features:
  • Step-by-step configuration wizard
  • Visual preview of what will be deleted
  • Multiple confirmation prompts for safety
  • Progress bars and status updates
  • Color-coded warnings and information

═══════════════════════════════════════════════════════════════════════════
NON-INTERACTIVE MODE (For Scripts & Automation)
═══════════════════════════════════════════════════════════════════════════

Use command-line arguments for scripting and cron jobs:

    python prune.py --days 60 --execute
    python prune.py --dry-run  # Preview only
    python prune.py --delete-inactive-users-days 180 --execute

Common Options:
  --dry-run                    Preview what will be deleted (safe)
  --execute                    Actually perform deletions

Age-Based Deletion:
  --days N                     Delete chats older than N days
  --exempt-archived-chats      Keep archived chats even if old
  --exempt-chats-in-folders    Keep organized chats

User Deletion:
  --delete-inactive-users-days N    Delete users inactive for N+ days
  --exempt-admin-users              Never delete admins (RECOMMENDED)
  --exempt-pending-users            Never delete pending users

Orphaned Data:
  --delete-orphaned-chats           Delete orphaned chats
  --delete-orphaned-tools           Delete orphaned tools
  --delete-orphaned-functions       Delete orphaned functions
  --delete-orphaned-prompts         Delete orphaned prompts
  --delete-orphaned-knowledge-bases Delete orphaned knowledge bases
  --delete-orphaned-models          Delete orphaned models
  --delete-orphaned-notes           Delete orphaned notes
  --delete-orphaned-folders         Delete orphaned folders

Other:
  --audio-cache-max-age-days N Delete audio cache older than N days
  --run-vacuum                  Run VACUUM to reclaim disk space
  --verbose, -v                 Enable debug logging
  --quiet, -q                   Suppress all but errors

═══════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════

Preview what would be deleted:
    python prune.py --dry-run

Delete chats older than 90 days:
    python prune.py --days 90 --execute

Delete inactive users (180+ days) and their data:
    python prune.py --delete-inactive-users-days 180 --execute

Full cleanup with optimization:
    python prune.py --days 60 --delete-inactive-users-days 180 \\
      --audio-cache-max-age-days 30 --run-vacuum --execute

═══════════════════════════════════════════════════════════════════════════
SAFETY FEATURES
═══════════════════════════════════════════════════════════════════════════

✓ Dry-run mode by default (must use --execute for actual deletion)
✓ File-based locking prevents concurrent operations
✓ Multiple confirmation prompts in interactive mode
✓ Admin users exempted by default
✓ Comprehensive logging of all operations
✓ Preview counts before execution

═══════════════════════════════════════════════════════════════════════════
GETTING HELP
═══════════════════════════════════════════════════════════════════════════

Documentation:
  • README.md - Complete usage guide
  • ANALYSIS.md - Technical details and feasibility analysis
  • FEATURES.md - Complete feature catalog
  • example_cron.txt - Automation examples

For detailed non-interactive options:
    python standalone_prune.py --help

For more information, visit:
    https://github.com/open-webui/open-webui
"""
    print(help_text)


if __name__ == "__main__":
    sys.exit(main())
