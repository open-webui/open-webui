import peewee as pw


def key_text(database: pw.Database, *, max_length: int = 255, **kwargs) -> pw.Field:
    """
    Dialect-aware "text-like" field for Peewee migrations:
    - MySQL/MariaDB: use VARCHAR(max_length) so UNIQUE/PK/INDEX works without prefix lengths.
    - Postgres/SQLite: keep TEXT to preserve existing schema/history.
    """
    if isinstance(database, pw.MySQLDatabase):
        return pw.CharField(max_length=max_length, **kwargs)
    return pw.TextField(**kwargs)
