import json
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from open_webui.models.users import UserModel
from open_webui.utils.luxtronic import (
    DEFAULT_MODEL,
    get_luxtronic_model_names,
    user_can_access_lux_model,
)
import seed_luxtronic


def _make_user(role: str = "user", tenant_id: str | None = None) -> UserModel:
    return UserModel(
        id=str(uuid4()),
        name="Test User",
        email="user@example.com",
        username=None,
        role=role,
        profile_image_url="/user.png",
        bio=None,
        gender=None,
        date_of_birth=None,
        info=None,
        settings=None,
        api_key=None,
        oauth_sub=None,
        tenant_id=tenant_id,
        last_active_at=0,
        updated_at=0,
        created_at=0,
    )


def test_admin_gets_all_luxtronic_models(monkeypatch):
    monkeypatch.setattr(
        "open_webui.utils.luxtronic.Tenants.get_all_model_names",
        lambda: ["alpha_q", "beta_q"],
    )
    user = _make_user(role="admin")
    assert get_luxtronic_model_names(user) == ["alpha_q", "beta_q"]


def test_user_only_sees_tenant_models(monkeypatch):
    tenant_id = "tenant-42"
    monkeypatch.setattr(
        "open_webui.utils.luxtronic.Tenants.get_model_names_for_tenant",
        lambda tid: ["foo_q", "bar_q"] if tid == tenant_id else [],
    )
    user = _make_user(role="user", tenant_id=tenant_id)
    assert get_luxtronic_model_names(user, restrict_to_user=True) == [
        "foo_q",
        "bar_q",
    ]


def test_user_can_access_specific_model(monkeypatch):
    tenant_id = "tenant-123"
    monkeypatch.setattr(
        "open_webui.utils.luxtronic.Tenants.get_model_names_for_tenant",
        lambda _: ["foo_q"],
    )
    user = _make_user(role="user", tenant_id=tenant_id)
    assert user_can_access_lux_model(user, "luxor:foo_q")
    assert not user_can_access_lux_model(user, "luxor:bar_q")


def test_default_model_used_when_no_tenants(monkeypatch):
    monkeypatch.setattr(
        "open_webui.utils.luxtronic.Tenants.get_all_model_names",
        lambda: [],
    )
    assert get_luxtronic_model_names(None) == [DEFAULT_MODEL]


def test_seed_script_creates_tenant_and_user(monkeypatch):
    created_tenants = {}
    created_users = []

    def fake_get_tenant_by_name(name):
        return created_tenants.get(name)

    def fake_create_tenant(form):
        tenant = SimpleNamespace(id=str(uuid4()), name=form.name, model_names=form.model_names)
        created_tenants[tenant.name] = tenant
        return tenant

    def fake_update_tenant(tenant_id, form):
        tenant = created_tenants[next(iter(created_tenants))]
        if form.model_names:
            tenant.model_names = form.model_names
        return tenant

    monkeypatch.setattr("seed_luxtronic.Tenants.get_tenant_by_name", fake_get_tenant_by_name)
    monkeypatch.setattr("seed_luxtronic.Tenants.create_tenant", fake_create_tenant)
    monkeypatch.setattr("seed_luxtronic.Tenants.update_tenant", fake_update_tenant)

    def fake_get_user_by_email(email):
        for user in created_users:
            if user.email == email:
                return user
        return None

    def fake_update_user_by_id(user_id, payload):
        for user in created_users:
            if user.id == user_id:
                user.role = payload.get("role", user.role)
                user.tenant_id = payload.get("tenant_id", user.tenant_id)
                return user
        return None

    monkeypatch.setattr("seed_luxtronic.Users.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr("seed_luxtronic.Users.update_user_by_id", fake_update_user_by_id)

    def fake_insert_new_auth(**kwargs):
        user = SimpleNamespace(
            id=str(uuid4()),
            email=kwargs["email"],
            role=kwargs.get("role", "user"),
            tenant_id=kwargs.get("tenant_id"),
        )
        created_users.append(user)
        return user

    def fake_update_password(user_id, hashed):
        return True

    monkeypatch.setattr("seed_luxtronic.Auths.insert_new_auth", fake_insert_new_auth)
    monkeypatch.setattr("seed_luxtronic.Auths.update_user_password_by_id", fake_update_password)

    payload = [
        {
            "name": "Seed Tenant",
            "model_names": ["seed_q"],
            "users": [
                {
                    "email": "seed@example.com",
                    "password": "Secret123!",
                    "role": "admin",
                }
            ],
        }
    ]

    os.environ["LUXTRONIC_TENANT_SEED"] = json.dumps(payload)
    try:
        seed_luxtronic.main()
    finally:
        os.environ.pop("LUXTRONIC_TENANT_SEED", None)

    assert "Seed Tenant" in created_tenants
    assert created_tenants["Seed Tenant"].model_names == ["seed_q"]
    assert any(user.email == "seed@example.com" and user.role == "admin" for user in created_users)
