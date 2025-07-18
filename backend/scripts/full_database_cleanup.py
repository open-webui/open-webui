#!/usr/bin/env python3
"""
Complete Database Cleanup Tool for CANChat
Cleans up both SQLite database entries and Qdrant vector collections
(local dev only)
"""

import sys
import os

sys.path.append("./backend")

from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT


def get_all_vector_collections():
    """Get all collections from Qdrant"""
    try:
        if hasattr(VECTOR_DB_CLIENT, "client") and hasattr(
            VECTOR_DB_CLIENT.client, "get_collections"
        ):
            collections_response = VECTOR_DB_CLIENT.client.get_collections()
            return [col.name for col in collections_response.collections]
        else:
            print("❌ Cannot list collections from this vector DB type")
            return []
    except Exception as e:
        print(f"❌ Error getting collections: {e}")
        return []


def cleanup_orphaned_database_entries():
    """Clean up database entries that don't have corresponding vector collections"""
    print("\n🧹 Cleaning up orphaned database entries...")

    # Get all vector collections
    vector_collections = set(get_all_vector_collections())
    print(f"   Found {len(vector_collections)} vector collections")

    # Check files
    print("\n📁 Checking files...")
    try:
        all_files = Files.get_files()
        orphaned_files = []

        for file in all_files:
            expected_collection = f"file-{file.id}"
            if expected_collection not in vector_collections:
                orphaned_files.append(file)

        if orphaned_files:
            print(f"   Found {len(orphaned_files)} orphaned files:")
            for file in orphaned_files:
                print(f"   - {file.filename} (ID: {file.id})")

            confirm = input(
                f"\n🗑️  Delete these {len(orphaned_files)} orphaned files from database? (y/N): "
            )
            if confirm.lower() == "y":
                for file in orphaned_files:
                    try:
                        Files.delete_file_by_id(file.id)
                        print(f"   ✅ Deleted file: {file.filename}")
                    except Exception as e:
                        print(f"   ❌ Error deleting file {file.filename}: {e}")
        else:
            print("   ✅ No orphaned files found")

    except Exception as e:
        print(f"   ❌ Error checking files: {e}")

    # Check knowledge bases
    print("\n📚 Checking knowledge bases...")
    try:
        all_knowledge = Knowledges.get_knowledge_bases()
        orphaned_knowledge = []

        for kb in all_knowledge:
            # Knowledge collections can be UUID format
            if kb.id not in vector_collections:
                orphaned_knowledge.append(kb)

        if orphaned_knowledge:
            print(f"   Found {len(orphaned_knowledge)} orphaned knowledge bases:")
            for kb in orphaned_knowledge:
                print(f"   - {kb.name} (ID: {kb.id})")

            confirm = input(
                f"\n🗑️  Delete these {len(orphaned_knowledge)} orphaned knowledge bases from database? (y/N): "
            )
            if confirm.lower() == "y":
                for kb in orphaned_knowledge:
                    try:
                        Knowledges.delete_knowledge_by_id(kb.id)
                        print(f"   ✅ Deleted knowledge base: {kb.name}")
                    except Exception as e:
                        print(f"   ❌ Error deleting knowledge base {kb.name}: {e}")
        else:
            print("   ✅ No orphaned knowledge bases found")

    except Exception as e:
        print(f"   ❌ Error checking knowledge bases: {e}")


def cleanup_orphaned_vector_collections():
    """Clean up vector collections that don't have corresponding database entries"""
    print("\n🔍 Checking for orphaned vector collections...")

    vector_collections = get_all_vector_collections()
    orphaned_collections = []

    # Get all valid IDs from database
    try:
        all_files = Files.get_files()
        valid_file_ids = {f"file-{file.id}" for file in all_files}
    except:
        valid_file_ids = set()

    try:
        all_knowledge = Knowledges.get_knowledge_bases()
        valid_kb_ids = {kb.id for kb in all_knowledge}
    except:
        valid_kb_ids = set()

    for collection in vector_collections:
        is_orphaned = False

        if collection.startswith("file-"):
            if collection not in valid_file_ids:
                is_orphaned = True
        elif collection.startswith("web_"):
            # Keep web collections for now
            continue
        else:
            # Assume it's a knowledge base (UUID format)
            if collection not in valid_kb_ids:
                is_orphaned = True

        if is_orphaned:
            orphaned_collections.append(collection)

    if orphaned_collections:
        print(f"   Found {len(orphaned_collections)} orphaned vector collections:")
        for collection in orphaned_collections:
            print(f"   - {collection}")

        confirm = input(
            f"\n🗑️  Delete these {len(orphaned_collections)} orphaned vector collections? (y/N): "
        )
        if confirm.lower() == "y":
            for collection in orphaned_collections:
                try:
                    VECTOR_DB_CLIENT.delete_collection(collection)
                    print(f"   ✅ Deleted vector collection: {collection}")
                except Exception as e:
                    print(f"   ❌ Error deleting collection {collection}: {e}")
    else:
        print("   ✅ No orphaned vector collections found")


def cleanup_old_web_searches():
    """Clean up old web search collections"""
    print("\n🌐 Checking web search collections...")

    vector_collections = get_all_vector_collections()
    web_collections = [c for c in vector_collections if c.startswith("web_")]

    if web_collections:
        print(f"   Found {len(web_collections)} web search collections:")
        for collection in web_collections:
            print(f"   - {collection}")

        confirm = input(
            f"\n🗑️  Delete ALL {len(web_collections)} web search cache collections? (y/N): "
        )
        if confirm.lower() == "y":
            for collection in web_collections:
                try:
                    VECTOR_DB_CLIENT.delete_collection(collection)
                    print(f"   ✅ Deleted web collection: {collection}")
                except Exception as e:
                    print(f"   ❌ Error deleting collection {collection}: {e}")
    else:
        print("   ✅ No web search collections found")


def show_final_stats():
    """Show final statistics"""
    print("\n📊 Final Database Statistics:")

    try:
        files = Files.get_files()
        print(f"   Files in database: {len(files)}")
    except:
        print("   Files in database: Unable to count")

    try:
        knowledge = Knowledges.get_knowledge_bases()
        print(f"   Knowledge bases in database: {len(knowledge)}")
    except:
        print("   Knowledge bases in database: Unable to count")

    vector_collections = get_all_vector_collections()
    print(f"   Vector collections: {len(vector_collections)}")

    web_collections = [c for c in vector_collections if c.startswith("web_")]
    file_collections = [c for c in vector_collections if c.startswith("file-")]
    other_collections = [
        c
        for c in vector_collections
        if not c.startswith("web_") and not c.startswith("file-")
    ]

    print(f"   - Web search collections: {len(web_collections)}")
    print(f"   - File collections: {len(file_collections)}")
    print(f"   - Knowledge collections: {len(other_collections)}")


def main():
    print("🧹 CANChat Complete Database Cleanup Tool")
    print("=" * 50)
    print()
    print("This tool will:")
    print("1. Remove database entries that don't have vector collections")
    print("2. Remove vector collections that don't have database entries")
    print("3. Optionally clean up web search caches")
    print()

    choice = input("Do you want to proceed? (y/N): ")
    if choice.lower() != "y":
        print("❌ Cleanup cancelled")
        return

    # Step 1: Clean up orphaned database entries
    cleanup_orphaned_database_entries()

    # Step 2: Clean up orphaned vector collections
    cleanup_orphaned_vector_collections()

    # Step 3: Optionally clean up web searches
    cleanup_old_web_searches()

    # Show final stats
    show_final_stats()

    print("\n🎉 Complete cleanup finished!")


if __name__ == "__main__":
    main()
