import os
import textwrap
import logging
from pathlib import Path
from datetime import datetime

from wisp import PROJECT_DIR
from wisp.protobuf import service_pb2
from wisp.exceptions import WispError
from wisp.protobuf.common_pb2 import Session
from open_webui.env import SRC_LOG_LEVELS
from .asciinema import AsciinemaWriter
from ..base import BaseWisp

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class ReplayHandler(BaseWisp):
    DEFAULT_ENCODING = "utf-8"
    REPLAY_DIR = os.path.join(PROJECT_DIR, 'data/replay')

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.replay_writer = None
        self.file_writer = None
        self.file = None
        self.build_file()

    def build_file(self):
        self.ensure_replay_dir()

        replay_file_path = os.path.join(self.REPLAY_DIR, f"{self.session.id}.cast")
        file = Path(replay_file_path)

        try:
            if file.exists():
                file.unlink()

            file.touch()
            self.file = file
            self.file_writer = file.open(mode="w", encoding=self.DEFAULT_ENCODING)
            self.replay_writer = AsciinemaWriter(self.file_writer)
            self.replay_writer.write_header()
        except Exception as e:
            error_message = f'Failed to create replay file: {file.name} -> {e}'
            logger.error(error_message)

    def ensure_replay_dir(self):
        os.makedirs(self.REPLAY_DIR, exist_ok=True)

    def write_row(self, row):
        row = row.replace("\n", "\r\n")
        row = row.replace("\r\r\n", "\r\n")
        row = f"{row} \r\n"

        try:
            self.replay_writer.write_row(row.encode(self.DEFAULT_ENCODING))
        except Exception as e:
            error_message = f'Failed to write replay row: {e}'
            logger.error(error_message)

    async def write_input(self, input_str):
        # TODO 后续时间处理要统一
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        input_str = f"[{formatted_time}]#: {input_str}"
        self.write_row(input_str)

    async def write_output(self, output_str):
        wrapper = textwrap.TextWrapper(width=self.replay_writer.WIDTH)
        output_str = wrapper.fill(output_str)
        output_str = f"\r\n {output_str} \r\n"
        self.write_row(output_str)

    async def upload(self):
        try:
            self.file_writer.close()
            replay_request = service_pb2.ReplayRequest(
                session_id=self.session.id,
                replay_file_path=self.file.absolute().as_posix()
            )
            resp = self.stub.UploadReplayFile(replay_request)

            if not resp.status.ok:
                error_message = f'Failed to upload replay file: {self.file.name} {resp.status.err}'
                logger.error(error_message)
                raise WispError(error_message)
        except Exception as e:
            logger.error(f'Failed to upload replay file upload {e}')
