"""
sync_tools_startup.py
=====================
Wird beim Docker-Start automatisch ausgeführt.
Liest alle .py-Dateien aus /tools-sync/ und synchronisiert sie
via direkten SQLite-DB-Zugriff in die OpenWebUI-Datenbank.

Ignoriert:
  - __init__.py
  - builtin.py
  - sync_*.py  (dieses Skript selbst)
"""

import os
import re
import sys
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format="[TOOL-SYNC] %(message)s")
log = logging.getLogger("tool-sync")

TOOLS_DIR = "/tools-sync"
DB_PATH   = "/app/backend/data/webui.db"

# Warte bis die DB existiert (OpenWebUI initialisiert sie beim ersten Start)
def wait_for_db(path: str, max_wait: int = 60):
    for i in range(max_wait):
        if os.path.exists(path):
            return True
        log.info(f"Warte auf Datenbank... ({i+1}s)")
        time.sleep(1)
    return False


def extract_meta(content: str) -> tuple[str, str, str]:
    title = re.search(r'title:\s*(.+)', content)
    desc  = re.search(r'description:\s*\|?\s*\n?((?:[ \t]+.+\n?)+)', content)
    ver   = re.search(r'version:\s*(.+)', content)
    title_str = title.group(1).strip() if title else None
    desc_str  = desc.group(1).strip()  if desc  else ""
    ver_str   = ver.group(1).strip()   if ver   else "1.0.0"
    return title_str, desc_str, ver_str


def make_tool_id(title: str, filename: str) -> str:
    base = title or os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_')


def sync_tools():
    if not os.path.isdir(TOOLS_DIR):
        log.warning(f"Tools-Verzeichnis '{TOOLS_DIR}' nicht gefunden – Sync übersprungen.")
        return

    if not wait_for_db(DB_PATH):
        log.error(f"Datenbank '{DB_PATH}' nicht gefunden nach 60s – Abbruch.")
        sys.exit(1)

    # sqlite3 ist in Python stdlib – keine externen Packages nötig
    import sqlite3

    py_files = [
        f for f in os.listdir(TOOLS_DIR)
        if f.endswith(".py")
        and not f.startswith("__")
        and not f.startswith("sync_")
        and f not in ("builtin.py",)
    ]

    if not py_files:
        log.info("Keine Tool-Dateien gefunden.")
        return

    log.info(f"{len(py_files)} Tool-Datei(en) gefunden: {', '.join(py_files)}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Sicherstellen dass die tool-Tabelle existiert
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool'")
    if not cur.fetchone():
        log.warning("Tabelle 'tool' existiert noch nicht – warte 5s und versuche erneut...")
        con.close()
        time.sleep(5)
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

    synced = 0
    for filename in py_files:
        filepath = os.path.join(TOOLS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            title, description, version = extract_meta(content)
            tool_id = make_tool_id(title, filename)
            tool_name = title or tool_id
            now = int(time.time())

            # Prüfen ob Tool bereits existiert
            cur.execute("SELECT id FROM tool WHERE id = ?", (tool_id,))
            exists = cur.fetchone()

            meta = json.dumps({
                "description": description,
                "manifest": {"version": version}
            })

            if exists:
                cur.execute("""
                    UPDATE tool SET name=?, content=?, meta=?, updated_at=?
                    WHERE id=?
                """, (tool_name, content, meta, now, tool_id))
                log.info(f"✅ UPDATED:  '{tool_name}' (id={tool_id}) aus {filename}")
            else:
                # user_id = "" → kein spezifischer User-Owner (Admin-Tool)
                cur.execute("""
                    INSERT INTO tool (id, user_id, name, content, specs, meta, valves, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tool_id, "", tool_name, content, "[]", meta, "{}", now, now))
                log.info(f"✨ CREATED:  '{tool_name}' (id={tool_id}) aus {filename}")

            synced += 1

        except Exception as e:
            log.error(f"❌ Fehler bei '{filename}': {e}")

    con.commit()
    con.close()
    log.info(f"Sync abgeschlossen: {synced}/{len(py_files)} Tools synchronisiert.")


if __name__ == "__main__":
    sync_tools()
