import asyncio
from types import SimpleNamespace

from open_webui.models.access_grants import AccessGrants, normalize_access_grants
from open_webui.models.models import Models
from open_webui.utils.access_control import has_base_model_access


def inherit_grant():
    return {
        'principal_type': 'model',
        'principal_id': '*',
        'permission': 'inherit',
    }


def test_normalize_accepts_only_wildcard_model_inherit_for_model_resources():
    accepted = normalize_access_grants([inherit_grant()], resource_type='model')

    assert [
        {
            'principal_type': grant['principal_type'],
            'principal_id': grant['principal_id'],
            'permission': grant['permission'],
        }
        for grant in accepted
    ] == [inherit_grant()]

    assert normalize_access_grants([inherit_grant()], resource_type='tool') == []
    assert (
        normalize_access_grants(
            [{**inherit_grant(), 'principal_id': 'specific-model'}],
            resource_type='model',
        )
        == []
    )
    assert (
        normalize_access_grants(
            [{**inherit_grant(), 'permission': 'read'}],
            resource_type='model',
        )
        == []
    )


async def deny_direct_access(**_kwargs):
    return False


def patch_models(monkeypatch, models_by_id):
    async def get_model_by_id(model_id, db=None):
        return models_by_id.get(model_id)

    monkeypatch.setattr(Models, 'get_model_by_id', get_model_by_id)
    monkeypatch.setattr(AccessGrants, 'has_access', deny_direct_access)


def test_protected_base_allows_same_owner_wrapper(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='owner', base_model_id='base')
    base = SimpleNamespace(
        id='base',
        user_id='owner',
        base_model_id=None,
        access_grants=[inherit_grant()],
    )
    patch_models(monkeypatch, {'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is True


def test_protected_base_denies_different_owner_wrapper(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='wrapper-owner', base_model_id='base')
    base = SimpleNamespace(
        id='base',
        user_id='base-owner',
        base_model_id=None,
        access_grants=[inherit_grant()],
    )
    patch_models(monkeypatch, {'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is False


def test_private_base_still_denies_mediated_access(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='owner', base_model_id='base')
    base = SimpleNamespace(id='base', user_id='owner', base_model_id=None, access_grants=[])
    patch_models(monkeypatch, {'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is False


def test_protected_chain_allows_matching_owner_at_every_edge(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='owner', base_model_id='middle')
    middle = SimpleNamespace(
        id='middle',
        user_id='owner',
        base_model_id='base',
        access_grants=[inherit_grant()],
    )
    base = SimpleNamespace(
        id='base',
        user_id='owner',
        base_model_id=None,
        access_grants=[inherit_grant()],
    )
    patch_models(monkeypatch, {'middle': middle, 'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is True


def test_protected_chain_denies_owner_mismatch_at_deeper_edge(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='owner', base_model_id='middle')
    middle = SimpleNamespace(
        id='middle',
        user_id='owner',
        base_model_id='base',
        access_grants=[inherit_grant()],
    )
    base = SimpleNamespace(
        id='base',
        user_id='other-owner',
        base_model_id=None,
        access_grants=[inherit_grant()],
    )
    patch_models(monkeypatch, {'middle': middle, 'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is False


def test_base_model_cycle_fails_closed(monkeypatch):
    wrapper = SimpleNamespace(id='wrapper', user_id='owner', base_model_id='base')
    base = SimpleNamespace(
        id='base',
        user_id='owner',
        base_model_id='wrapper',
        access_grants=[inherit_grant()],
    )
    patch_models(monkeypatch, {'base': base})

    assert asyncio.run(has_base_model_access('caller', wrapper, user_role='user')) is False
