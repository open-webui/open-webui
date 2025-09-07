import json
import time
from datetime import datetime


class AsciinemaWriter:
    VERSION = 2
    WIDTH = 80
    HEIGHT = 40
    DEFAULT_SHELL = "/bin/bash"
    DEFAULT_TERM = "xterm"
    NEW_LINE = "\n"

    def __init__(self, writer):
        self.config = {
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "envShell": self.DEFAULT_SHELL,
            "envTerm": self.DEFAULT_TERM,
            "timestamp": int(datetime.timestamp(datetime.now())),
            "title": None
        }
        self.writer = writer
        self.timestampNano = time.time_ns()

    def write_header(self):
        header = {
            "version": self.VERSION,
            "width": self.config["width"],
            "height": self.config["height"],
            "timestamp": self.config["timestamp"],
            "title": self.config["title"],
            "env": {
                "shell": self.config["envShell"],
                "term": self.config["envTerm"]
            }
        }
        json_data = json.dumps(header) + self.NEW_LINE
        self.writer.write(json_data)

    def write_row(self, p):
        now = time.time_ns()
        ts = (now - self.timestampNano) / 1_000_000_000.0
        self.write_stdout(ts, p)

    def write_stdout(self, ts, data):
        row = [ts, "o", data.decode("utf-8")]
        json_data = json.dumps(row) + self.NEW_LINE
        self.writer.write(json_data)
