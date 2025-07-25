#!/usr/bin/env python3
"""
Cleanup Script for processed_generations Table (REFERENCE IMPLEMENTATION)
========================================================================

⚠️  IMPORTANT: This is a REFERENCE IMPLEMENTATION for manual use only.

The automatic cleanup functionality is now INTEGRATED into the mAI Usage system:
- Location: backend/open_webui/utils/background_sync.py (lines 558-576)  
- Scheduling: Runs automatically every day at midnight
- Configuration: 90-day retention period
- Monitoring: Full audit logging in processed_generation_cleanup_log table

This standalone script is kept for:
- Manual cleanup operations (if needed)
- Debugging and testing
- Reference implementation

For production deployments, use the integrated automatic cleanup system.

