#!/usr/bin/env python3
"""
Comprehensive cleanup script for CANChat Vector DB and Database
This script performs aggressive cleanup of orphaned data
(local dev only)
"""

import sys
import os

sys.path.append("./backend")

import requests
import json
from open_webui.models.knowledge import Knowledges
from open_webui.models.files import Files
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT


def authenticate_and_get_token():
    """Authenticate with the API and return token"""
    auth_url = "http://localhost:8080/api/v1/auths/signin"
    auth_data = {"email": "sam.mueller@ssc-spc.gc.ca", "password": "adminadmin"}

    print("🔐 Authenticating...")
    auth_response = requests.post(auth_url, json=auth_data)
    if auth_response.status_code == 200:
        token = auth_response.json().get("token")
        print("✅ Authentication successful!")
        return token
    else:
        print("❌ Authentication failed")
        return None


def get_vector_collections():
    """Get all collections from Qdrant"""
    try:
        if hasattr(VECTOR_DB_CLIENT, "client") and hasattr(
            VECTOR_DB_CLIENT.client, "get_collections"
        ):
            collections_response = VECTOR_DB_CLIENT.client.get_collections()
            return [col.name for col in collections_response.collections]
        else:
            print("❌ Cannot access Qdrant collections")
            return []
    except Exception as e:
        print(f"❌ Error getting collections: {e}")
        return []


def check_database_references():
    """Check what knowledge bases and files exist in the database"""
    print("\n📋 Checking database references...")

    # Check knowledge bases
    try:
        knowledge_bases = Knowledges.get_all()
        print(f"   Knowledge bases in DB: {len(knowledge_bases)}")
        kb_ids = []
        for kb in knowledge_bases:
            print(f"   - KB: {kb.id} (name: {kb.name})")
            kb_ids.append(kb.id)
    except Exception as e:
        print(f"   Error checking knowledge bases: {e}")
        kb_ids = []

    # Check files
    try:
        files = Files.get_all()
        print(f"   Files in DB: {len(files)}")
        file_ids = []
        for file in files:
            print(f"   - File: {file.id} (name: {file.filename})")
            file_ids.append(file.id)
    except Exception as e:
        print(f"   Error checking files: {e}")
        file_ids = []

    return kb_ids, file_ids


def aggressive_cleanup():
    """Perform aggressive cleanup of orphaned collections"""
    print("\n🧹 Starting aggressive cleanup...")

    # Get all vector collections
    collections = get_vector_collections()
    print(f"   Found {len(collections)} vector collections")

    # Get database references
    kb_ids, file_ids = check_database_references()

    collections_to_delete = []

    for collection in collections:
        should_delete = False
        reason = ""

        # Check file collections
        if collection.startswith("file-"):
            file_id = collection.replace("file-", "")
            if file_id not in file_ids:
                should_delete = True
                reason = f"File {file_id} not found in database"

        # Check knowledge collections (UUID format)
        elif len(collection) == 36 and "-" in collection:  # UUID format
            if collection not in kb_ids:
                should_delete = True
                reason = f"Knowledge base {collection} not found in database"

        # Check web search collections older than 1 day
        elif collection.startswith("web_"):
            # For this demo, we'll be conservative with web collections
            print(f"   Web collection found: {collection} (keeping for now)")

        if should_delete:
            collections_to_delete.append((collection, reason))

    # Show what would be deleted
    if collections_to_delete:
        print(f"\n❗ Found {len(collections_to_delete)} orphaned collections:")
        for collection, reason in collections_to_delete:
            print(f"   - {collection}: {reason}")

        # Ask for confirmation
        response = input(
            f"\n🗑️  Delete these {len(collections_to_delete)} orphaned collections? (y/N): "
        )
        if response.lower() == "y":
            deleted_count = 0
            for collection, reason in collections_to_delete:
                try:
                    VECTOR_DB_CLIENT.delete_collection(collection)
                    print(f"   ✅ Deleted: {collection}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to delete {collection}: {e}")

            print(f"\n🎉 Cleanup complete! Deleted {deleted_count} collections")
        else:
            print("   Cleanup cancelled by user")
    else:
        print("   ✅ No orphaned collections found")


def api_cleanup(token):
    """Use the API endpoints for cleanup"""
    headers = {"Authorization": f"Bearer {token}"}

    print("\n🌐 API-based cleanup...")

    # Health check
    health_url = "http://localhost:8080/api/v1/retrieval/maintenance/health/vector-db"
    response = requests.get(health_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        vector_db = data.get("vector_db", {})
        print(
            f"   Current state: {vector_db.get('total_collections', 0)} total collections"
        )

    # Comprehensive cleanup
    cleanup_url = "http://localhost:8080/api/v1/retrieval/maintenance/cleanup/comprehensive?max_age_days=1"
    response = requests.post(cleanup_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print("   ✅ API cleanup completed")
        if "cleanup_results" in result:
            orphaned = result["cleanup_results"].get("orphaned_vectors", {})
            web_search = result["cleanup_results"].get("web_search_vectors", {})
            print(f"   - Orphaned: {orphaned.get('collections_cleaned', 0)} cleaned")
            print(
                f"   - Web search: {web_search.get('collections_cleaned', 0)} cleaned"
            )


def main():
    print("🧹 CANChat Comprehensive Cleanup Tool")
    print("=====================================")

    # Method 1: Direct database/vector cleanup
    print("\n📋 Method 1: Direct Database Analysis & Cleanup")
    aggressive_cleanup()

    # Method 2: API-based cleanup
    print("\n📋 Method 2: API-based Cleanup")
    token = authenticate_and_get_token()
    if token:
        api_cleanup(token)

    # Final stats
    print("\n📊 Final Statistics:")
    collections = get_vector_collections()
    print(f"   Remaining vector collections: {len(collections)}")
    for collection in collections:
        print(f"   - {collection}")


if __name__ == "__main__":
    main()
