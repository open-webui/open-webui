"""Account input, persistence, and concurrent NFC uniqueness regressions."""

import asyncio
import importlib
import secrets
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from open_webui.utils.email import register_sqlite_email_normalization

NFD_EMAIL = 'ame\u0301lie@bu\u0308cher.example'
NFC_EMAIL = 'amélie@bücher.example'


@pytest.fixture(scope='module')
def models(tmp_path_factory):
    # Import account models without touching the application's configured database.
    data_dir = tmp_path_factory.mktemp('email-accounts-config')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('DATA_DIR', str(data_dir))
        patch.setenv('DATABASE_URL', f'sqlite:///{data_dir}/unused.db')
        patch.setenv('USE_SLIM_DOCKER', 'true')
        patch.setenv('OFFLINE_MODE', 'true')
        patch.setenv('ENABLE_DB_MIGRATIONS', 'false')
        patch.setenv('WEBUI_SECRET_KEY', secrets.token_urlsafe(32))
        auths = importlib.import_module('open_webui.models.auths')
        users = importlib.import_module('open_webui.models.users')
        db = importlib.import_module('open_webui.internal.db')
        patch.setattr(db, 'DATABASE_ENABLE_SESSION_SHARING', True)
        yield SimpleNamespace(auths=auths, users=users, db=db)


@pytest_asyncio.fixture
async def sessions(models, tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/accounts.db')
    register_sqlite_email_normalization(engine)
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda conn: models.db.Base.metadata.create_all(
                conn, tables=[models.users.User.__table__, models.auths.Auth.__table__]
            )
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.parametrize('form_name', ['SigninForm', 'SignupForm', 'AddUserForm', 'UserUpdateForm'])
def test_account_request_forms_normalize_only_email(models, form_name):
    module = models.users if form_name == 'UserUpdateForm' else models.auths
    form = getattr(module, form_name)(name='Ame\u0301lie', email=NFD_EMAIL, password='unchanged-e\u0301')
    assert form.email == NFC_EMAIL
    assert form.password == 'unchanged-e\u0301'
    if hasattr(form, 'name'):
        assert form.name == 'Ame\u0301lie'


def test_partial_user_update_does_not_invent_email(models):
    assert models.users.UserUpdateForm(name='Changed').email is None
    assert models.users.UserUpdateForm(email=None).email is None


@pytest.mark.asyncio
@pytest.mark.parametrize('first, second', [(NFD_EMAIL, NFC_EMAIL), (NFC_EMAIL, NFD_EMAIL)])
async def test_account_creation_stores_nfc_and_rejects_equivalent_email(models, sessions, first, second):
    async with sessions() as db:
        user = await models.auths.Auths.insert_new_auth(first, 'password-hash', 'Amélie', db=db)
        assert user.email == NFC_EMAIL
        # SQL text bypasses the ORM so this checks the actual stored bytes.
        assert (await db.execute(text('SELECT email FROM "user"'))).scalar_one() == NFC_EMAIL
        assert (await db.execute(text('SELECT email FROM auth'))).scalar_one() == NFC_EMAIL
        with pytest.raises(IntegrityError):
            await models.auths.Auths.insert_new_auth(second, 'other-hash', 'Duplicate', db=db)
        assert (await db.execute(select(func.count()).select_from(models.users.User))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(models.auths.Auth))).scalar_one() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('stored_email', [NFD_EMAIL, NFD_EMAIL.upper(), NFC_EMAIL.upper()])
async def test_existing_nfd_account_is_found_and_cannot_be_registered_twice(models, sessions, stored_email):
    async with sessions() as db:
        # Simulate a legacy row written before application normalization existed.
        await db.execute(
            text(
                'INSERT INTO "user" (id, email, name, role, created_at, updated_at, last_active_at) '
                'VALUES (:id, :email, :name, :role, 0, 0, 0)'
            ),
            {'id': 'legacy', 'email': stored_email, 'name': 'Amélie', 'role': 'user'},
        )
        await db.execute(
            text('INSERT INTO auth (id, email, password, active) VALUES (:id, :email, :password, 1)'),
            {'id': 'legacy', 'email': stored_email, 'password': 'legacy-hash'},
        )
        await db.commit()
        for spelling in (NFD_EMAIL, NFC_EMAIL, stored_email):
            assert (await models.users.Users.get_user_by_email(spelling, db=db)).id == 'legacy'
            verifier = AsyncMock(return_value=True)
            user, _ = await models.auths.Auths.authenticate_user(spelling, verifier, db=db)
            assert user.id == 'legacy'
            verifier.assert_awaited_once_with('legacy-hash')
        with pytest.raises(IntegrityError):
            await models.auths.Auths.insert_new_auth(NFC_EMAIL, 'other-hash', 'Duplicate', db=db)
        assert (await db.execute(select(func.count()).select_from(models.auths.Auth))).scalar_one() == 1


@pytest.mark.asyncio
async def test_concurrent_canonical_equivalent_registration_creates_one_account(models, sessions):
    barrier = asyncio.Barrier(2)

    async def register(email):
        async with sessions() as db:
            # Both registrations pass the early lookup before either writes.
            assert await models.users.Users.get_user_by_email(email, db=db) is None
            await barrier.wait()
            return await models.auths.Auths.insert_new_auth(email, 'password-hash', 'Amélie', db=db)

    outcomes = await asyncio.gather(register(NFD_EMAIL), register(NFC_EMAIL), return_exceptions=True)
    assert sum(isinstance(result, IntegrityError) for result in outcomes) == 1
    assert sum(isinstance(result, models.users.UserModel) for result in outcomes) == 1
    async with sessions() as db:
        assert (await db.execute(text('SELECT email FROM "user"'))).scalar_one() == NFC_EMAIL
        assert (await db.execute(text('SELECT email FROM auth'))).scalar_one() == NFC_EMAIL


@pytest.mark.asyncio
async def test_user_and_auth_updates_store_nfc(models, sessions):
    async with sessions() as db:
        user = await models.auths.Auths.insert_new_auth('original@example.com', 'hash', 'Amélie', db=db)
        await models.auths.Auths.update_email_by_id(user.id, NFD_EMAIL, db=db)
        updated = await models.users.Users.update_user_by_id(user.id, {'email': NFD_EMAIL}, db=db)
        assert updated.email == NFC_EMAIL
        assert (await db.execute(text('SELECT email FROM "user"'))).scalar_one() == NFC_EMAIL
        assert (await db.execute(text('SELECT email FROM auth'))).scalar_one() == NFC_EMAIL


@pytest.mark.asyncio
async def test_rejected_email_update_keeps_user_and_auth_consistent(models, sessions):
    async with sessions() as db:
        await models.auths.Auths.insert_new_auth(NFC_EMAIL, 'hash', 'First', db=db)
        other = await models.auths.Auths.insert_new_auth('other@example.com', 'hash', 'Other', db=db)
        other_id = other.id
        with pytest.raises(IntegrityError):
            await models.auths.Auths.update_email_by_id(other_id, NFD_EMAIL, db=db)
        await db.rollback()
        for table in ('user', 'auth'):
            assert (
                await db.execute(text(f'SELECT email FROM "{table}" WHERE id = :id'), {'id': other_id})
            ).scalar_one() == 'other@example.com'
