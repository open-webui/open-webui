"""
sync_tools_startup.py
=====================
Wird beim Docker-Start automatisch ausgeführt.
Liest alle .py-Dateien aus /tools-sync/ und synchronisiert sie
via direkten SQLite-DB-Zugriff in die OpenWebUI-Datenbank.

Extrahiert automatisch:
  - Tool-Metadaten (title, description, version) aus dem Docstring
  - Function-Specs (für OpenWebUI Tool Calling)
  - Valve-Defaults (aus Valves & UserValves Klassen)

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
import inspect

logging.basicConfig(level=logging.INFO, format="[TOOL-SYNC] %(message)s")
log = logging.getLogger("tool-sync")

TOOLS_DIR = "/tools-sync"
DB_PATH   = "/app/backend/data/webui.db"


def wait_for_db(path: str, max_wait: int = 60):
    for i in range(max_wait):
        if os.path.exists(path):
            return True
        log.info(f"Warte auf Datenbank... ({i+1}s)")
        time.sleep(1)
    return False


def extract_meta(content: str) -> tuple:
    title = re.search(r'title:\s*(.+)', content)
    desc  = re.search(r'description:\s*\|?\s*\n?((?:[ \t]+.+\n?)+)', content)
    ver   = re.search(r'version:\s*(.+)', content)
    title_str = title.group(1).strip() if title else None
    desc_str  = re.sub(r'\n\s+', ' ', desc.group(1)).strip() if desc else ""
    ver_str   = ver.group(1).strip() if ver else "1.0.0"
    return title_str, desc_str, ver_str


def make_tool_id(title: str, filename: str) -> str:
    base = title or os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_')


def python_type_to_json_schema(annotation) -> dict:
    """Konvertiert Python-Typ-Annotierungen zu JSON Schema."""
    import typing
    origin = getattr(annotation, '__origin__', None)
    
    if annotation is inspect.Parameter.empty or annotation is None:
        return {"type": "string"}
    
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    # Optional[X] → X (nullable)
    if origin is typing.Union:
        args = [a for a in annotation.__args__ if a is not type(None)]
        if args:
            return python_type_to_json_schema(args[0])
    
    return {"type": type_map.get(annotation, "string")}


def extract_param_description(docstring: str, param_name: str) -> str:
    """Extrahiert die Beschreibung eines Parameters aus dem Docstring."""
    if not docstring:
        return ""
    pattern = rf':param\s+{re.escape(param_name)}\s*:\s*(.+?)(?=:param|\Z)'
    match = re.search(pattern, docstring, re.DOTALL)
    if match:
        return match.group(1).strip().replace('\n', ' ')
    return ""


def extract_function_description(docstring: str) -> str:
    """Extrahiert die Hauptbeschreibung aus dem Docstring (vor :param)."""
    if not docstring:
        return ""
    lines = []
    for line in docstring.strip().split('\n'):
        if line.strip().startswith(':'):
            break
        lines.append(line.strip())
    return ' '.join(filter(None, lines)).strip()


def extract_specs(module_globals: dict) -> list:
    """Extrahiert Function-Specs aus der Tools-Klasse für OpenWebUI."""
    Tools = module_globals.get('Tools')
    if not Tools:
        return []
    
    specs = []
    for method_name, method in inspect.getmembers(Tools, predicate=inspect.isfunction):
        if method_name.startswith('_'):
            continue
        
        sig = inspect.signature(method)
        doc = inspect.getdoc(method) or ""
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            annotation = param.annotation
            schema = python_type_to_json_schema(annotation)
            
            param_desc = extract_param_description(
                inspect.getdoc(method) or "", param_name
            )
            if param_desc:
                schema["description"] = param_desc
            
            # Default-Wert
            if param.default is not inspect.Parameter.empty:
                default = param.default
                if default is not None:
                    schema["default"] = default
            else:
                required.append(param_name)
            
            properties[param_name] = schema
        
        func_desc = extract_function_description(doc)
        
        spec = {
            "name": method_name,
            "description": func_desc or method_name,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
        specs.append(spec)
    
    return specs




def load_module(filepath: str, content: str) -> dict:
    """Führt den Tool-Code aus und gibt den globalen Namespace zurück."""
    module_globals = {}
    try:
        exec(compile(content, filepath, 'exec'), module_globals)
        return module_globals
    except Exception as e:
        log.warning(f"  Konnte Modul nicht laden: {e}")
        return {}


def sync_tools():
    if not os.path.isdir(TOOLS_DIR):
        log.warning(f"Tools-Verzeichnis '{TOOLS_DIR}' nicht gefunden – Sync übersprungen.")
        return

    if not wait_for_db(DB_PATH):
        log.error(f"Datenbank '{DB_PATH}' nicht gefunden nach 60s – Abbruch.")
        sys.exit(1)

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

    # Warten bis Tabelle existiert
    for _ in range(10):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool'")
        if cur.fetchone():
            break
        log.info("Warte auf tool-Tabelle...")
        time.sleep(2)

    # Spalten prüfen (für Kompatibilität mit verschiedenen OpenWebUI-Versionen)
    cur.execute("PRAGMA table_info(tool)")
    columns = {row[1] for row in cur.fetchall()}
    has_valves_column = "valves" in columns

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

            # Modul laden für Specs und Valves
            module_globals = load_module(filepath, content)

            specs = extract_specs(module_globals)
            specs_json   = json.dumps(specs, ensure_ascii=False)
            meta_json    = json.dumps({
                "description": description,
                "manifest": {"version": version}
            }, ensure_ascii=False)

            log.info(f"  → {len(specs)} Funktion(en) extrahiert")

            cur.execute("SELECT id FROM tool WHERE id = ?", (tool_id,))
            exists = cur.fetchone()

            if exists:
                cur.execute(
                    "UPDATE tool SET name=?, content=?, specs=?, meta=?, updated_at=? WHERE id=?",
                    (tool_name, content, specs_json, meta_json, now, tool_id)
                )
                log.info(f"✅ UPDATED:  '{tool_name}' (id={tool_id})")
            else:
                if has_valves_column:
                    cur.execute(
                        """INSERT INTO tool (id, user_id, name, content, specs, meta, valves, updated_at, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (tool_id, "", tool_name, content, specs_json, meta_json, None, now, now)
                    )
                else:
                    cur.execute(
                        """INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (tool_id, "", tool_name, content, specs_json, meta_json, now, now)
                    )
                log.info(f"✨ CREATED:  '{tool_name}' (id={tool_id})")

            synced += 1

        except Exception as e:
            log.error(f"❌ Fehler bei '{filename}': {e}")
            import traceback
            traceback.print_exc()

    con.commit()
    con.close()
    log.info(f"Sync abgeschlossen: {synced}/{len(py_files)} Tools synchronisiert.")


if __name__ == "__main__":
    sync_tools()
