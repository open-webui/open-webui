from peewee import *
from config import DATA_DIR
import os


# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    print("File renamed successfully.")
else:
    pass


DB = SqliteDatabase(f"{DATA_DIR}/webui.db")
DB.connect()
