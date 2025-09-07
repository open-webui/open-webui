import os
import queue
import logging
import asyncio
import threading

from wisp import PROJECT_DIR
from wisp.protobuf import service_pb2
from wisp.exceptions import WispError
from wisp.protobuf.common_pb2 import KillSession
from open_webui.env import SRC_LOG_LEVELS
from .base import BaseWisp
from .session import JMSSession

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class PollJMSEvent(BaseWisp):
    @staticmethod
    async def close_session(target_session: JMSSession):
        await target_session.close()

    def clear_zombie_session(self):
        replay_dir = os.path.join(PROJECT_DIR, 'data/replay')
        req = service_pb2.RemainReplayRequest(replay_dir=replay_dir)
        resp = self.stub.ScanRemainReplays(req)
        if not resp.status.ok:
            error_message = f'Failed to scan remain replay: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        else:
            logger.info('Scan remain replay success')

    def wait_for_kill_session_message(self):
        from jms import session_manager
        q = queue.Queue(maxsize=1000)
        for resp in self.stub.DispatchTask(iter(q.get, None)):
            task = resp.task
            task_id = task.id
            session_id = task.session_id
            task_action = task.action
            target_session = None
            for jms_session in session_manager.get_store().values():
                if isinstance(jms_session, JMSSession) and jms_session.session.id == session_id:
                    target_session = jms_session
                    break
            if target_session is not None:
                if task_action == KillSession:
                    asyncio.run(self.close_session(target_session))

                req = service_pb2.FinishedTaskRequest(task_id=target_session.session.id)
                self.stub.FinishSession(req)

    def start_session_killer(self):
        self.wait_for_kill_session_message()

    def start(self):
        self.clear_zombie_session()
        self.start_session_killer()


def setup_poll_jms_event():
    jms_event = PollJMSEvent()
    thread = threading.Thread(target=jms_event.start)
    thread.start()
