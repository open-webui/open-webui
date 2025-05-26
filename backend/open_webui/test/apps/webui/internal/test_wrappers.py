import pytest
import os
from unittest.mock import patch, MagicMock, call
from peewee import PostgresqlDatabase, SqliteDatabase

from open_webui.internal.wrappers import register_connection


class TestWrappers:
    """Test cases for the wrappers.py module, focusing on DATABASE_SCHEMA functionality."""

    def test_register_connection_postgresql_with_schema(self):
        """Test PostgreSQL connection when DATABASE_SCHEMA is set."""
        with patch('open_webui.internal.wrappers.DATABASE_SCHEMA', 'test_schema'):
            with patch('open_webui.internal.wrappers.connect') as mock_connect, \
                 patch('open_webui.internal.wrappers.parse') as mock_parse, \
                 patch('open_webui.internal.wrappers.ReconnectingPostgresqlDatabase') as mock_db_class:
                
                # Mock PostgreSQL database
                mock_pg_db = MagicMock(spec=PostgresqlDatabase)
                mock_connect.return_value = mock_pg_db
                
                # Mock parse result without existing options
                mock_parse.return_value = {
                    'database': 'testdb',
                    'user': 'testuser',
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432
                }
                
                # Mock database instance
                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                
                # Test
                db_url = "postgresql://testuser:testpass@localhost:5432/testdb"
                result = register_connection(db_url)
                
                # Assertions
                mock_connect.assert_called_once_with(db_url, unquote_user=True, unquote_password=True)
                mock_parse.assert_called_once_with(db_url, unquote_user=True, unquote_password=True)
                
                # Check that options were added with schema
                expected_connection = {
                    'database': 'testdb',
                    'user': 'testuser', 
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432,
                    'options': '-c search_path=test_schema,public'
                }
                mock_db_class.assert_called_once_with(**expected_connection)
                mock_db_instance.connect.assert_called_once_with(reuse_if_open=True)
                
                # Verify the returned database is the mock instance
                assert result == mock_db_instance

    def test_register_connection_postgresql_with_schema_existing_options(self):
        """Test PostgreSQL connection when DATABASE_SCHEMA is set and options already exist."""
        with patch('open_webui.internal.wrappers.DATABASE_SCHEMA', 'test_schema'):
            with patch('open_webui.internal.wrappers.connect') as mock_connect, \
                 patch('open_webui.internal.wrappers.parse') as mock_parse, \
                 patch('open_webui.internal.wrappers.ReconnectingPostgresqlDatabase') as mock_db_class:
                
                # Mock PostgreSQL database
                mock_pg_db = MagicMock(spec=PostgresqlDatabase)
                mock_connect.return_value = mock_pg_db
                
                # Mock parse result with existing options
                mock_parse.return_value = {
                    'database': 'testdb',
                    'user': 'testuser',
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432,
                    'options': '-c some_existing_option=value'
                }
                
                # Mock database instance
                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                
                # Test
                db_url = "postgresql://testuser:testpass@localhost:5432/testdb"
                result = register_connection(db_url)
                
                # Check that schema was appended to existing options
                expected_connection = {
                    'database': 'testdb',
                    'user': 'testuser', 
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432,
                    'options': '-c some_existing_option=value -c search_path=test_schema,public'
                }
                mock_db_class.assert_called_once_with(**expected_connection)

    def test_register_connection_postgresql_without_schema(self):
        """Test PostgreSQL connection when DATABASE_SCHEMA is not set."""
        with patch('open_webui.internal.wrappers.DATABASE_SCHEMA', None):
            with patch('open_webui.internal.wrappers.connect') as mock_connect, \
                 patch('open_webui.internal.wrappers.parse') as mock_parse, \
                 patch('open_webui.internal.wrappers.ReconnectingPostgresqlDatabase') as mock_db_class:
                
                # Mock PostgreSQL database
                mock_pg_db = MagicMock(spec=PostgresqlDatabase)
                mock_connect.return_value = mock_pg_db
                
                # Mock parse result
                mock_parse.return_value = {
                    'database': 'testdb',
                    'user': 'testuser',
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432
                }
                
                # Mock database instance
                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                
                # Test
                db_url = "postgresql://testuser:testpass@localhost:5432/testdb"
                result = register_connection(db_url)
                
                # Check that no schema options were added
                expected_connection = {
                    'database': 'testdb',
                    'user': 'testuser', 
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432
                }
                mock_db_class.assert_called_once_with(**expected_connection)

    def test_register_connection_postgresql_empty_schema(self):
        """Test PostgreSQL connection when DATABASE_SCHEMA is empty string."""
        with patch('open_webui.internal.wrappers.DATABASE_SCHEMA', ''):
            with patch('open_webui.internal.wrappers.connect') as mock_connect, \
                 patch('open_webui.internal.wrappers.parse') as mock_parse, \
                 patch('open_webui.internal.wrappers.ReconnectingPostgresqlDatabase') as mock_db_class:
                
                # Mock PostgreSQL database
                mock_pg_db = MagicMock(spec=PostgresqlDatabase)
                mock_connect.return_value = mock_pg_db
                
                # Mock parse result
                mock_parse.return_value = {
                    'database': 'testdb',
                    'user': 'testuser',
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432
                }
                
                # Mock database instance
                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                
                # Test
                db_url = "postgresql://testuser:testpass@localhost:5432/testdb"
                result = register_connection(db_url)
                
                # Check that no schema options were added (empty string is falsy)
                expected_connection = {
                    'database': 'testdb',
                    'user': 'testuser', 
                    'password': 'testpass',
                    'host': 'localhost',
                    'port': 5432
                }
                mock_db_class.assert_called_once_with(**expected_connection)

    def test_register_connection_sqlite(self):
        """Test SQLite connection (should not be affected by DATABASE_SCHEMA)."""
        with patch('open_webui.internal.wrappers.DATABASE_SCHEMA', 'test_schema'):
            with patch('open_webui.internal.wrappers.connect') as mock_connect:
                
                # Mock SQLite database
                mock_sqlite_db = MagicMock(spec=SqliteDatabase)
                mock_connect.return_value = mock_sqlite_db
                
                # Test
                db_url = "sqlite:///test.db"
                result = register_connection(db_url)
                
                # Assertions
                mock_connect.assert_called_once_with(db_url, unquote_user=True, unquote_password=True)
                
                # Verify SQLite database properties are set
                assert mock_sqlite_db.autoconnect is True
                assert mock_sqlite_db.reuse_if_open is True
                
                # Verify the returned database is the mock instance
                assert result == mock_sqlite_db

    def test_register_connection_unsupported_database(self):
        """Test that unsupported database types raise ValueError."""
        with patch('open_webui.internal.wrappers.connect') as mock_connect:
            
            # Mock an unsupported database type
            mock_unsupported_db = MagicMock()
            # Make it not an instance of PostgresqlDatabase or SqliteDatabase
            mock_unsupported_db.__class__ = type('UnsupportedDB', (), {})
            mock_connect.return_value = mock_unsupported_db
            
            # Test
            db_url = "mysql://user:pass@localhost/db"
            
            with pytest.raises(ValueError, match="Unsupported database connection"):
                register_connection(db_url)

    @patch('open_webui.internal.wrappers.log')
    def test_register_connection_postgresql_logging(self, mock_log):
        """Test that PostgreSQL connection logs the correct message."""
        with patch('open_webui.internal.wrappers.connect') as mock_connect, \
             patch('open_webui.internal.wrappers.parse') as mock_parse, \
             patch('open_webui.internal.wrappers.ReconnectingPostgresqlDatabase') as mock_db_class:
            
            # Mock PostgreSQL database
            mock_pg_db = MagicMock(spec=PostgresqlDatabase)
            mock_connect.return_value = mock_pg_db
            mock_parse.return_value = {'database': 'test'}
            mock_db_class.return_value = MagicMock()
            
            # Test
            register_connection("postgresql://user:pass@localhost/db")
            
            # Check logging
            mock_log.info.assert_called_with("Connected to PostgreSQL database")

    @patch('open_webui.internal.wrappers.log')
    def test_register_connection_sqlite_logging(self, mock_log):
        """Test that SQLite connection logs the correct message."""
        with patch('open_webui.internal.wrappers.connect') as mock_connect:
            
            # Mock SQLite database
            mock_sqlite_db = MagicMock(spec=SqliteDatabase)
            mock_connect.return_value = mock_sqlite_db
            
            # Test
            register_connection("sqlite:///test.db")
            
            # Check logging
            mock_log.info.assert_called_with("Connected to SQLite database") 
