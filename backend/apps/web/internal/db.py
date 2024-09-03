from peewee import *
from peewee_migrate import Router
from playhouse.db_url import connect
from config import SRC_LOG_LEVELS, DATA_DIR, DATABASE_URL
import os
import logging
import json

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)
        

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass

DB = connect(DATABASE_URL)
log.info(f"Connected to a {DB.__class__.__name__} database.")
router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)
router.run()
DB.connect(reuse_if_open=True)


from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib
from config import MSSQL_SERVER, MSSQL_USER, MSSQL_PASSWORD, MSSQL_DATABASE

Base = declarative_base()

class DatabaseConnection:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string, echo=True)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_all(self):
        Base.metadata.create_all(self.engine)

    def query(self, model):
        return self.session.query(model)

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()

log.info("Creating a connection to the MSSQL database.")
params = urllib.parse.quote_plus(f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={MSSQL_SERVER};DATABASE={MSSQL_DATABASE};UID={MSSQL_USER};PWD={MSSQL_PASSWORD};Encrypt=Yes;TrustServerCertificate=Yes')
connection_string = f"mssql+pyodbc:///?odbc_connect=%s" %  params
MSSQL_DB = DatabaseConnection(connection_string)
log.info("Connected to the MSSQL database.")
