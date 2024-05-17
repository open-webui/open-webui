from peewee_migrate import Router
from db import DB, log

router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)

def migrate():
    router.run()

if __name__ == "__main__":
    migrate()