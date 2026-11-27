"""
title: JARVIS Barehands
author: JoshTXWC
description: Control the Barehands hand-tracked glass stage (https://github.com/jaredrhod/barehands, AGPL-3.0) - open it, present cards, add cards, set the ring state. Ported from JoshTXWC/JARVIS barehands_tools.
version: 1.0.0
license: MIT
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from pydantic import BaseModel, Field

_proc = None


def _default_dir() -> str:
    home = os.environ.get("JARVIS_HOME", "")
    if home:
        return str(Path(home) / "integrations" / "barehands")
    return str(Path.home() / "JARVIS" / "integrations" / "barehands")


class Tools:
    class Valves(BaseModel):
        BAREHANDS_DIR: str = Field(default="", description="Folder that holds barehands server.py. Empty = JARVIS_HOME/integrations/barehands.")
        PORT: int = Field(default=8794)
        PYTHON: str = Field(default="", description="Python used to run server.py. Empty = the Python running Open WebUI.")

    def __init__(self):
        self.valves = self.Valves()

    # -- helpers --------------------------------------------------------------
    def _root(self) -> Path:
        return Path(os.path.expanduser(self.valves.BAREHANDS_DIR or os.environ.get("JARVIS_BAREHANDS_DIR", "") or _default_dir()))

    def _url(self, page: str = "stage.html") -> str:
        return f"http://127.0.0.1:{self.valves.PORT}/{page}"

    def _port_open(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.valves.PORT), timeout=0.4):
                return True
        except OSError:
            return False

    def _ensure_running(self, timeout_s: float = 20.0) -> None:
        global _proc
        if self._port_open():
            return
        root = self._root()
        if not (root / "server.py").exists():
            raise RuntimeError(
                f"Barehands is not installed at {root}. Run setup.bat again, or: "
                f"git clone --depth 1 https://github.com/jaredrhod/barehands.git \"{root}\""
            )
        cfg = root / "barehands.json"
        if not cfg.exists():
            cfg.write_text(json.dumps({"name": "JARVIS", "port": self.valves.PORT}, indent=2) + "\n", encoding="utf-8")
        if _proc is None or _proc.poll() is not None:
            logf = open(root / "jarvis-barehands.log", "a", encoding="utf-8")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            _proc = subprocess.Popen(
                [self.valves.PYTHON or sys.executable, "server.py"], cwd=str(root),
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
                stdout=logf, stderr=subprocess.STDOUT, creationflags=flags,
            )
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self._port_open():
                return
            if _proc.poll() is not None:
                raise RuntimeError(f"Barehands exited early (code {_proc.returncode}); see {root / 'jarvis-barehands.log'}")
            time.sleep(0.25)
        raise TimeoutError(f"Barehands did not open port {self.valves.PORT} in {timeout_s}s")

    def _cmd(self, payload: dict) -> None:
        self._ensure_running()
        req = urllib.request.Request(
            self._url("cmd"), data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()

    def _ring(self, state: str) -> None:
        try:
            p = self._root() / "state" / "state"
            if (self._root() / "server.py").exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(state, encoding="utf-8")
        except Exception:
            pass

    # -- tools ----------------------------------------------------------------
    def barehands_open(self) -> str:
        """
        Open the Barehands hand-tracked glass stage (webcam hand UI). Use for: barehands, bare hands, hands mode, hand tracking.
        """
        try:
            self._ensure_running()
            self._ring("listening")
            return (f"Barehands stage is live: [open the stage]({self._url()}). "
                    "In the JARVIS desktop app press Ctrl+Shift+H for the fullscreen overlay. Allow the camera and wave.")
        except Exception as e:
            return f"Error: {e}"

    def barehands_close(self) -> str:
        """
        Close Barehands hands mode and stop the stage server JARVIS started.
        """
        global _proc
        self._ring("idle")
        if _proc is not None and _proc.poll() is None:
            _proc.terminate()
            _proc = None
            return "Barehands stage stopped."
        return "Barehands set to idle (it was not started by this JARVIS session, so it is left running)."

    def barehands_present(self, title: str, body: str = "") -> str:
        """
        Put a card centre-stage on the Barehands glass board ("show me", "put it up on the board").
        :param title: Card title.
        :param body: Card text.
        """
        try:
            self._cmd({"a": "present", "title": title, "body": body or ""})
            return f"Presented \"{title}\" on the Barehands board ({self._url()})."
        except Exception as e:
            return f"Error: {e}"

    def barehands_add_card(self, title: str, body: str = "") -> str:
        """
        Add a glass card to the Barehands board without spotlighting it.
        :param title: Card title.
        :param body: Card text.
        """
        try:
            self._cmd({"a": "add_card", "title": title, "body": body or ""})
            return f"Card \"{title}\" added to Barehands."
        except Exception as e:
            return f"Error: {e}"

    def barehands_status(self) -> str:
        """
        Report whether Barehands is installed and running.
        """
        root = self._root()
        return json.dumps({"installed": (root / "server.py").exists(), "dir": str(root),
                           "running": self._port_open(), "url": self._url()})
