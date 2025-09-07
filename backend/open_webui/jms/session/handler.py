import asyncio
import logging
from datetime import datetime
from typing import Optional

import socketio

from wisp.protobuf import service_pb2
from wisp.exceptions import WispError
from wisp.protobuf.common_pb2 import TokenAuthInfo, Session
from open_webui.env import SRC_LOG_LEVELS
from ..schemas import CommandRecord, JMSState, AskResponse, AskResponseType, reply
from ..replay import ReplayHandler
from ..command import CommandHandler
from ..base import BaseWisp

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class JMSSession(BaseWisp):
    def __init__(self, session: Session, auth_info: TokenAuthInfo, sio: socketio.AsyncServer, sid: str):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.session = session
        self.history_asks = []
        self.current_ask_interrupt = False
        self.command_acls = list(auth_info.filter_rules)
        self.expire_time = auth_info.expire_info.expire_at
        self.max_idle_time_delta = auth_info.setting.max_idle_time

        self.command_handler = None
        self.replay_handler = None
        self.jms_state = JMSState(id=session.id)

    def active_session(self) -> None:
        self.replay_handler = ReplayHandler(self.session)
        self.command_handler = CommandHandler(
            self.session, self.command_acls, self.jms_state, self.sio, self.sid
        )
        asyncio.create_task(self.maximum_idle_time_detection())

    async def maximum_idle_time_detection(self):
        last_active_time = datetime.now()

        while True:
            current_time = datetime.now()
            idle_time = current_time - last_active_time

            if idle_time.total_seconds() >= self.max_idle_time_delta * 60:
                await self.close()
                break

            if self.jms_state.new_dialogue:
                last_active_time = current_time
                self.jms_state.new_dialogue = False

            await asyncio.sleep(3)

    async def close_session(self) -> None:
        req = service_pb2.SessionFinishRequest(
            id=self.session.id,
            date_end=int(datetime.now().timestamp())
        )
        resp = self.stub.FinishSession(req)

        if not resp.status.ok:
            error_message = f'Failed to close session: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)

    async def close(self) -> None:
        from jms import session_manager
        self.current_ask_interrupt = True
        await asyncio.sleep(1)
        await self.replay_handler.upload()
        await self.close_session()
        session_manager.unregister_jms_session(self)
        await self.notify_to_close()

    async def notify_to_close(self):
        await reply(
            self.websocket, AskResponse(
                type=AskResponseType.finish,
                conversation_id=self.session.id,
                system_message='Session interrupted'
            )
        )

    async def with_audit(self, command: str, chat_func):
        command_record = CommandRecord(input=command)
        self.command_handler.command_record = command_record
        try:
            is_continue = await self.command_handler.command_acl_filter()
            asyncio.create_task(self.replay_handler.write_input(command_record.input))
            if not is_continue:
                return

            result = await chat_func(self)
            command_record.output = result
            asyncio.create_task(self.replay_handler.write_output(command_record.output))
            return result

        except Exception as e:
            error = str(e)
            asyncio.create_task(self.replay_handler.write_output(error))
            raise e

        finally:
            asyncio.create_task(self.command_handler.record_command())


class SessionHandler(BaseWisp):

    def __init__(self, sio: socketio.AsyncServer, sid: str, scope: dict, auth_info: TokenAuthInfo):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.scope = scope
        self.auth_info = auth_info
        self.remote_address = self._get_remote_address()

    def _get_remote_address(self) -> Optional[str]:
        client = self.scope.get("client")
        ip = client[0] if client else None

        headers = dict(self.scope.get("headers", []))
        xff = headers.get(b"x-forwarded-for")
        xri = headers.get(b"x-real-ip")
        if xff:
            ip = xff.decode().split(",")[0].strip()
        elif xri:
            ip = xri.decode().strip()

        return ip

    def create_new_session(self, ai_model: str) -> JMSSession:
        session = self.create_session(self.auth_info, ai_model)
        jms_session = JMSSession(session, self.auth_info, self.sio, self.sid)
        return jms_session

    def create_session(self, auth_info: TokenAuthInfo, ai_model: str) -> Session:
        req_session = Session(
            user_id=auth_info.user.id,
            user=f'{auth_info.user.name}({auth_info.user.username})',
            account_id=auth_info.account.id,
            account=f'{auth_info.account.name}({auth_info.account.username})',
            org_id=auth_info.asset.org_id,
            asset_id=auth_info.asset.id,
            asset=auth_info.asset.name,
            login_from=Session.LoginFrom.WT,
            protocol=ai_model,
            date_start=int(datetime.now().timestamp()),
            remote_addr=self.remote_address,
        )
        req = service_pb2.SessionCreateRequest(data=req_session)
        resp = self.stub.CreateSession(req)
        if not resp.status.ok:
            error_message = f'Failed to create session: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return resp.data
