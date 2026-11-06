"""NFC account storage and migration regressions (SQLite and optional PostgreSQL)."""

import asyncio
import importlib.util
import os
import unicodedata
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from open_webui.utils.email import NFCEmail, email_key, email_nfc, normalize_email, register_sqlite_email_normalization


@pytest.mark.parametrize(
    'address',
    ['A\u0308nne@bu\u0308cher.example', 'δοκιμη\u0301@παρα\u0301δειγμα.example', '한@example.com'],
)
def test_normalize_email_composes_local_part_and_domain(address):
    assert normalize_email(address) == unicodedata.normalize('NFC', address)
    assert normalize_email(normalize_email(address)) == normalize_email(address)


@pytest.mark.parametrize('address', ['USER@EXAMPLE.COM', 'Straße@example.com', 'Ａ@example.com', 'legacy identifier'])
def test_nfc_does_not_change_case_compatibility_characters_or_syntax(address):
    assert normalize_email(address) == address


def test_database_expressions_compile_for_supported_dialects():
    expression = email_key(sa.column('email'))
    assert str(expression.compile(dialect=sqlite.dialect())) == 'unicode_email_key(email)'
    assert str(expression.compile(dialect=postgresql.dialect())) == 'normalize(lower(normalize(email, NFC)), NFC)'


_DATABASES = ['sqlite://']
if os.getenv('NFC_TEST_POSTGRES_URL'):
    _DATABASES.append(os.environ['NFC_TEST_POSTGRES_URL'])


@pytest.fixture(params=_DATABASES, ids=lambda value: 'postgresql' if value.startswith('postgres') else 'sqlite')
def connection(request):
    engine = sa.create_engine(request.param)
    register_sqlite_email_normalization(engine)
    # Calling twice must not add competing listeners.
    register_sqlite_email_normalization(engine)
    with engine.connect() as conn:
        transaction = conn.begin()
        if conn.dialect.name == 'postgresql':
            schema = 'nfc_test_' + uuid.uuid4().hex
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        else:
            conn.exec_driver_sql('BEGIN')
        try:
            yield conn
        finally:
            transaction.rollback()
    engine.dispose()


def test_type_normalizes_inserts_bulk_writes_and_updates(connection):
    metadata = sa.MetaData()
    table = sa.Table('account', metadata, sa.Column('id', sa.Integer, primary_key=True), sa.Column('email', NFCEmail()))
    metadata.create_all(connection)
    connection.execute(
        table.insert(),
        [
            {'id': 1, 'email': 'a\u0308@example.com'},
            {'id': 2, 'email': 'o\u0308@example.com'},
            {'id': 3, 'email': None},
        ],
    )
    assert connection.execute(sa.text('SELECT email FROM account ORDER BY id')).scalars().all() == [
        'ä@example.com',
        'ö@example.com',
        None,
    ]
    connection.execute(table.update().where(table.c.id == 1).values(email='u\u0308@bu\u0308cher.example'))
    assert connection.execute(sa.text('SELECT email FROM account WHERE id = 1')).scalar_one() == 'ü@bücher.example'


def test_async_sqlite_connections_register_normalization():
    async def exercise():
        engine = create_async_engine('sqlite+aiosqlite://')
        register_sqlite_email_normalization(engine)
        async with engine.begin() as conn:
            result = await conn.execute(sa.select(email_nfc(sa.literal('a\u0308@example.com'))))
            assert result.scalar_one() == 'ä@example.com'
            assert (await conn.execute(sa.select(email_nfc(sa.null())))).scalar_one() is None
        await engine.dispose()

    asyncio.run(exercise())


@pytest.fixture
def migration(monkeypatch):
    path = Path(__file__).parents[1] / 'open_webui/migrations/versions/7b9e2d1c4a60_normalize_account_emails_nfc.py'
    spec = importlib.util.spec_from_file_location('nfc_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.context, 'is_offline_mode', lambda: False)
    return module


def legacy_schema(connection):
    for table in ('user', 'auth'):
        connection.exec_driver_sql(f'CREATE TABLE "{table}" (id VARCHAR PRIMARY KEY, email VARCHAR)')
    connection.exec_driver_sql(
        'CREATE UNIQUE INDEX uq_user_email_lower ON "user" (lower(email)) WHERE email IS NOT NULL'
    )


def insert_account(connection, user_id, email):
    for table in ('user', 'auth'):
        connection.execute(
            sa.text(f'INSERT INTO "{table}" (id, email) VALUES (:id, :email)'), {'id': user_id, 'email': email}
        )


def upgrade(connection, migration):
    migration.op = Operations(MigrationContext.configure(connection))
    migration.upgrade()


def snapshot(connection):
    return {
        table: connection.execute(sa.text(f'SELECT id, email FROM "{table}" ORDER BY id')).all()
        for table in ('user', 'auth')
    }


def test_migration_composes_existing_user_and_auth_and_preserves_case(connection, migration):
    legacy_schema(connection)
    insert_account(connection, 'existing', 'A\u0308nne@bu\u0308cher.example')
    insert_account(connection, 'nullable', None)
    upgrade(connection, migration)
    for rows in snapshot(connection).values():
        assert rows == [('existing', 'Änne@bücher.example'), ('nullable', None)]
    # The migration never changes unrelated spelling rules or existing case policy.
    connection.execute(
        sa.text('INSERT INTO "user" (id, email) VALUES (:id, :email)'), {'id': 'distinct', 'email': 'anne@example.com'}
    )


@pytest.mark.parametrize(
    'first, second',
    [
        ('ä@example.com', 'a\u0308@example.com'),
        ('Ä@example.com', 'A\u0308@example.com'),
        ('ä@example.com', 'A\u0308@example.com'),
    ],
)
def test_migration_rejects_canonical_collisions_before_changes(connection, migration, first, second):
    legacy_schema(connection)
    insert_account(connection, 'first-id', first)
    insert_account(connection, 'second-id', second)
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match='first-id, second-id') as failure:
        upgrade(connection, migration)
    assert first not in str(failure.value)
    assert second not in str(failure.value)
    assert snapshot(connection) == before


@pytest.mark.parametrize('composed', ['ä@bücher.example', 'Ä@BÜCHER.example'])
@pytest.mark.parametrize('nfd_first', [True, False])
def test_index_blocks_raw_canonical_duplicate_inserts_in_both_orders(connection, migration, composed, nfd_first):
    legacy_schema(connection)
    upgrade(connection, migration)
    decomposed = unicodedata.normalize('NFD', composed)
    first, second = (decomposed, composed) if nfd_first else (composed, decomposed)
    insert_account(connection, 'first', first)
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            insert_account(connection, 'second', second)
    assert snapshot(connection) == {'user': [('first', first)], 'auth': [('first', first)]}


def test_index_blocks_raw_update_to_existing_canonical_email(connection, migration):
    legacy_schema(connection)
    insert_account(connection, 'first', 'ä@example.com')
    insert_account(connection, 'second', 'other@example.com')
    upgrade(connection, migration)
    before = snapshot(connection)
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            connection.execute(
                sa.text('UPDATE "user" SET email = :email WHERE id = :id'),
                {'id': 'second', 'email': 'a\u0308@example.com'},
            )
    assert snapshot(connection) == before


def test_downgrade_retains_canonical_storage_and_prior_case_index(connection, migration):
    legacy_schema(connection)
    insert_account(connection, 'first', 'a\u0308@example.com')
    upgrade(connection, migration)
    migration.downgrade()
    assert snapshot(connection)['user'] == [('first', 'ä@example.com')]
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            insert_account(connection, 'second', 'ä@EXAMPLE.COM')
