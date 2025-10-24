import os
import json
import time
import threading
import hashlib
import logging
from typing import Optional
from open_webui.config import PersistentConfig

log = logging.getLogger("open_webui.tool_servers.watcher")


def start_tool_server_connections_file_watcher(app, persistent_tool_server_connections):
    file_path = os.environ.get("TOOL_SERVER_CONNECTIONS_FILE")
    if file_path:
        watcher = ToolServerConnectionsFileWatcher(persistent_tool_server_connections, file_path)
        watcher.start()
        app.state.tool_server_connections_file_watcher = watcher

def stop_tool_server_connections_file_watcher(app):
    watcher = getattr(app.state, "tool_server_connections_file_watcher", None)
    if watcher:
        watcher.stop()


class ToolServerConnectionsFileWatcher:
    def __init__(self, persistent_config: PersistentConfig, file_path: str):
        self.persistent_config = persistent_config
        self.file_path = file_path
        self.poll_interval = 60  # seconds
        self._stop_event = threading.Event()
        self._last_signature = None
        self._last_content_hash = None

    def start(self):
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        log.info(f"[tool_servers/watch] Watcher started (interval={self.poll_interval}s, file='{self.file_path}')")

    def stop(self):
        self._stop_event.set()
        if hasattr(self, '_thread'):
            self._thread.join(timeout=2)
            log.info("[tool_servers/watch] Watcher stopped.")

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                self._check_once()
            except Exception as e:
                log.exception(f"[tool_servers/watch] Exception in poll loop: {e}")
            time.sleep(self.poll_interval)

    def _check_once(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, list):
                log.warning(f"[tool_servers/watch] File '{self.file_path}' does not contain a list; ignoring.")
                return
        except Exception as e:
            log.warning(f"[tool_servers/watch] Error reading file: {e}")
            return
        content_hash = hashlib.sha256(json.dumps(loaded, sort_keys=True).encode()).hexdigest()
        if content_hash == self._last_content_hash:
            return
        self._last_content_hash = content_hash
        self._handle_new_tool_servers(loaded)

    def _handle_new_tool_servers(self, file_list):
        self.persistent_config.update()
        def get_info_id(entry):
            if isinstance(entry, dict):
                info = entry.get('info')
                if isinstance(info, dict):
                    return info.get('id')
            return None

        current = self.persistent_config.value or []
        by_id = {get_info_id(entry): entry for entry in current if get_info_id(entry) is not None}
        for entry in file_list:
            entry_id = get_info_id(entry)
            if entry_id is not None:
                by_id[entry_id] = entry
        updated = list(by_id.values())
        if updated != current:
            log.info(f"[tool_servers/watch] Tool server(s) updated due to file change. New state: {updated}")
            self.persistent_config.value = updated
            self.persistent_config.save()