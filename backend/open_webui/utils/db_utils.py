# db_utils.py
import sqlite3
import os
from open_webui.env import TASKS_DATABASE_URL


# Cria diretório se necessário
db_dir = os.path.dirname(TASKS_DATABASE_URL)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


def init_db():
    con = sqlite3.connect(TASKS_DATABASE_URL)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS task_status (
            task_id TEXT PRIMARY KEY,
            status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    con.commit()
    con.close()


def store_status(task_id, status):
    con = sqlite3.connect(TASKS_DATABASE_URL)
    cur = con.cursor()
    cur.execute(
        '''
        INSERT INTO task_status (task_id, status)
        VALUES (?, ?)
        ON CONFLICT(task_id) DO UPDATE SET status=excluded.status, updated_at=CURRENT_TIMESTAMP
        ''',
        (task_id, status))
    con.commit()
    con.close()


def get_status(task_id):
    con = sqlite3.connect(TASKS_DATABASE_URL)
    cur = con.cursor()
    cur.execute('SELECT status FROM task_status WHERE task_id = ?', (task_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None
