#!/usr/bin/env python3
"""
Inspect child_profile and user tables to diagnose child account vs profile linkage.

Useful for debugging why email/password show "Not specified" in Profile Information.

Usage:
    cd backend && python scripts/inspect_child_data.py
    DB_ABS=/path/to/webui.db python scripts/inspect_child_data.py
"""

import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3


def get_db_path():
    """Resolve database path from DB_ABS or DATABASE_URL."""
    db_abs = os.environ.get("DB_ABS")
    if db_abs:
        if db_abs.startswith("sqlite://") or db_abs.startswith("sqlite+sqlcipher://"):
            path = (
                db_abs.replace("sqlite+sqlcipher://", "")
                .replace("sqlite://", "")
                .lstrip("/")
            )
            return (
                os.path.normpath(path) if os.path.isabs(path) else os.path.abspath(path)
            )
        return (
            os.path.normpath(db_abs)
            if os.path.isabs(db_abs)
            else os.path.abspath(db_abs)
        )

    from open_webui.env import DATABASE_URL, DATA_DIR

    if "sqlite" not in (DATABASE_URL or "").lower():
        print("Error: This script only works with SQLite. Set DB_ABS to your db path.")
        sys.exit(1)

    path = (
        DATABASE_URL.replace("sqlite+sqlcipher://", "")
        .replace("sqlite://", "")
        .lstrip("/")
    )
    if not os.path.isabs(path):
        path = os.path.join(DATA_DIR, path.lstrip("./"))
    return os.path.normpath(path)


def main():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}\n")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check tables exist
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('child_profile', 'user')"
    )
    tables = {r[0] for r in cur.fetchall()}
    if "child_profile" not in tables:
        print(
            "Warning: child_profile table not found. Run migrations: cd backend/open_webui && alembic upgrade head"
        )
    if "user" not in tables:
        print("Warning: user table not found.")
    if "child_profile" not in tables or "user" not in tables:
        conn.close()
        sys.exit(1)

    # 1. Child profiles
    cur.execute(
        "SELECT id, user_id, name, created_at FROM child_profile WHERE is_current = 1"
    )
    profiles = [dict(r) for r in cur.fetchall()]
    print(f"=== Child profiles (is_current=1): {len(profiles)} ===")
    for p in profiles:
        print(f"  id={p['id'][:8]}... user_id={p['user_id'][:8]}... name={p['name']!r}")

    # 2. Child user accounts (parent_id not null, role=child)
    cur.execute(
        "SELECT id, name, email, parent_id FROM \"user\" WHERE parent_id IS NOT NULL AND role = 'child'"
    )
    accounts = [dict(r) for r in cur.fetchall()]
    print(f"\n=== Child user accounts (role=child, parent_id set): {len(accounts)} ===")
    for a in accounts:
        print(
            f"  id={a['id'][:8]}... name={a['name']!r} email={a['email']!r} parent_id={a['parent_id'][:8]}..."
        )

    # 3. Match by name (profile.user_id = account.parent_id, profile.name = account.name)
    print("\n=== Name-based matching (profile.user_id = account.parent_id) ===")
    matched = []
    unmatched_profiles = []
    for p in profiles:
        found = False
        for a in accounts:
            if a["parent_id"] == p["user_id"] and (
                (p["name"] or "").strip().lower() == (a["name"] or "").strip().lower()
            ):
                matched.append((p, a))
                found = True
                break
        if not found:
            unmatched_profiles.append(p)

    for p, a in matched:
        print(f"  MATCH: profile {p['name']!r} -> account email={a['email']!r}")

    if unmatched_profiles:
        print(
            f"\n  Profiles WITHOUT matching child account ({len(unmatched_profiles)}):"
        )
        for p in unmatched_profiles:
            print(f"    - {p['name']!r} (user_id={p['user_id'][:8]}...)")

    matched_account_ids = {m[1]["id"] for m in matched}
    accounts_without_profile = [
        a for a in accounts if a["id"] not in matched_account_ids
    ]
    if accounts_without_profile:
        print(
            f"\n  Child accounts WITHOUT matching profile ({len(accounts_without_profile)}):"
        )
        for a in accounts_without_profile:
            print(f"    - {a['name']!r} email={a['email']!r}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
