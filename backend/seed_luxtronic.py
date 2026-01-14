import json
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from open_webui.internal.db import get_db
from open_webui.models.tenants import Tenants, TenantForm, TenantUpdateForm
from open_webui.models.users import Users
from open_webui.models.auths import Auths
from open_webui.utils.auth import get_password_hash
from sqlalchemy import text
import random
from datetime import datetime, timedelta

ENV_VAR = "LUXTRONIC_TENANT_SEED"


def load_seed() -> list[dict[str, Any]]:
    raw = os.environ.get(ENV_VAR)
    if not raw:
        print(f"{ENV_VAR} is not set. Nothing to seed.")
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {ENV_VAR}: {exc}") from exc

    if not isinstance(data, list):
        raise SystemExit(f"{ENV_VAR} must be a JSON array.")

    return data


def upsert_tenant(entry: dict[str, Any]):
    name = entry.get("name")
    if not name:
        raise SystemExit("Each tenant entry must include a 'name'.")
    
    s3_bucket = entry.get("s3_bucket")
    table_name = entry.get("table_name")
    system_config_client_name = entry.get("system_config_client_name")

    existing = Tenants.get_tenant_by_name(name)
    if existing:
        update_fields = {}
        if s3_bucket:
            update_fields["s3_bucket"] = s3_bucket
        if table_name:
            update_fields["table_name"] = table_name
        if system_config_client_name:
            update_fields["system_config_client_name"] = system_config_client_name
        if update_fields:
            Tenants.update_tenant(existing.id, TenantUpdateForm(**update_fields))
        tenant = Tenants.get_tenant_by_name(name)
        print(f"Tenant '{name}' already exists. Updating configuration.")
        try:
            upsert_tenant_schedule(tenant.id)
        except Exception as e:
            print(f"Warning: could not upsert tenant schedule for existing tenant {tenant.id}: {e}")
        return tenant
    
    tenant = Tenants.create_tenant(
        TenantForm(
            name=name,
            s3_bucket=s3_bucket,
            table_name=table_name,
            system_config_client_name=system_config_client_name,
        )
    )
    print(f"Created tenant '{name}'.")
    try:
        upsert_tenant_schedule(tenant.id)
    except Exception as e:
        print(f"Warning: could not upsert tenant schedule for new tenant {tenant.id}: {e}")
    return tenant


def upsert_user(tenant_id: str, entry: dict[str, Any]):
    email = entry.get("email")
    password = entry.get("password")
    if not email or not password:
        raise SystemExit("User entries must include 'email' and 'password'.")

    email = email.lower()
    name = entry.get("name") or email.split("@")[0]
    role = entry.get("role", "user")
    profile_image_url = entry.get("profile_image_url", "/user.png")

    existing = Users.get_user_by_email(email)
    hashed = get_password_hash(password)

    if existing:
        Users.update_user_by_id(
            existing.id,
            {
                "name": name,
                "role": role,
                "tenant_id": tenant_id,
                "profile_image_url": profile_image_url,
            },
        )
        Auths.update_user_password_by_id(existing.id, hashed)
        print(f"Updated user '{email}'.")
        return existing

    user = Auths.insert_new_auth(
        email=email,
        password=hashed,
        name=name,
        profile_image_url=profile_image_url,
        role=role,
        tenant_id=tenant_id,
    )
    print(f"Created user '{email}'.")
    return user


def upsert_tenant_schedule(tenant_id: str, interval_minutes: int = 60):
    offset_seconds = random.randint(0, interval_minutes * 60)
    next_run = datetime.utcnow() + timedelta(seconds=offset_seconds)
    sql = """
        INSERT INTO tenant_rebuild_schedule (tenant_id, interval_minutes, next_run, enabled)
        VALUES (:tenant_id, :interval_minutes, :next_run, 1)
        ON DUPLICATE KEY UPDATE
            interval_minutes = VALUES(interval_minutes),
            next_run = IFNULL(next_run, VALUES(next_run))
    """
    with get_db() as db:
        db.execute(
            text(sql),
            {
                "tenant_id": tenant_id,
                "interval_minutes": interval_minutes,
                "next_run": next_run,
            },
        )
        db.commit()


def main():
    seed_data = load_seed()
    if not seed_data:
        return

    for tenant_entry in seed_data:
        tenant = upsert_tenant(tenant_entry)
        for user_entry in tenant_entry.get("users", []):
            upsert_user(tenant.id, user_entry)


if __name__ == "__main__":
    main()
