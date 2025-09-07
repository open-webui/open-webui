import re
import time
import logging
import asyncio
from typing import List, Optional
from datetime import datetime

import socketio

from wisp.protobuf import service_pb2
from wisp.exceptions import WispError
from wisp.protobuf.common_pb2 import Session, CommandACL, RiskLevel
from open_webui.env import SRC_LOG_LEVELS
from .base import BaseWisp
from .schemas import CommandRecord, JMSState, AskResponse, AskResponseType, ResponseMeta, reply

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class CommandHandler(BaseWisp):
    WAIT_TICKET_TIMEOUT = 60 * 3
    WAIT_TICKET_INTERVAL = 2

    def __init__(
            self, session: Session,
            command_acls: List[CommandACL], jms_state: JMSState, sio: socketio.AsyncServer, sid: str
    ):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.session = session
        self.command_acls = command_acls
        self.cmd_acl_id = ''
        self.cmd_group_id = ''
        self.command_record: Optional[CommandRecord] = None
        self.jms_state = jms_state

    async def record_command(self):
        req = service_pb2.CommandRequest(
            sid=self.session.id,
            org_id=self.session.org_id,
            asset=self.session.asset,
            account=self.session.account,
            user=self.session.user,
            timestamp=int(datetime.timestamp(datetime.now())),
            input=self.command_record.input,
            output=self.command_record.output,
            risk_level=self.command_record.risk_level,
            cmd_acl_id=self.cmd_acl_id,
            cmd_group_id=self.cmd_group_id
        )
        resp = self.stub.UploadCommand(req)
        if not resp.status.ok:
            error_message = f'Failed to upload command: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)

    async def match_rule(self):
        for command_acl in self.command_acls:
            for command_group in command_acl.command_groups:
                flags = re.UNICODE
                if command_group.ignore_case:
                    flags |= re.IGNORECASE
                try:
                    pattern = re.compile(command_group.pattern, flags)
                    if pattern.search(self.command_record.input.lower()) is not None:
                        self.cmd_acl_id = command_acl.id
                        self.cmd_group_id = command_group.id
                        return command_acl
                except re.error as e:
                    error_message = f'Failed to re invalid pattern: {command_group.pattern} {e}'
                    logger.error(error_message)
                    # TODO Exception
                    raise Exception(error_message)

    async def create_and_wait_ticket(self, command_acl: CommandACL) -> bool:
        req = service_pb2.CommandConfirmRequest(
            cmd=self.command_record.input,
            session_id=self.session.id,
            cmd_acl_id=command_acl.id
        )
        resp = self.stub.CreateCommandTicket(req)
        if not resp.status.ok:
            error_message = f'Failed to create ticket: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)

        return await self.wait_for_ticket_status_change(resp.info)

    async def wait_for_ticket_status_change(self, ticket_info: service_pb2.TicketInfo):
        await reply(
            self.websocket, AskResponse(
                type=AskResponseType.waiting,
                conversation_id=self.session.id,
                system_message=(
                    'Review request has been initiated, please wait for review: {}'
                ).format(ticket_info.ticket_detail_url)
            )
        )
        start_time = time.time()
        end_time = start_time + self.WAIT_TICKET_TIMEOUT

        ticket_closed = False
        is_continue = False
        while time.time() <= end_time:
            check_request = service_pb2.TicketRequest(req=ticket_info.check_req)
            check_response: service_pb2.TicketStateResponse = self.stub.CheckTicketState(check_request)

            if not check_response.status.ok:
                error_message = f'Failed to check ticket status: {check_response.status.err}'
                logger.error(error_message)
                break
            system_message = ''
            state = check_response.Data.state
            if state == service_pb2.TicketState.Approved:
                self.command_record.risk_level = RiskLevel.ReviewAccept
                is_continue = True
                ticket_closed = True
                break
            elif state == service_pb2.TicketState.Rejected:
                self.command_record.risk_level = RiskLevel.ReviewReject
                ticket_closed = True
                system_message = 'The ticket is rejected'
            elif state == service_pb2.TicketState.Closed:
                self.command_record.risk_level = RiskLevel.ReviewCancel
                ticket_closed = False
                system_message = 'The ticket is closed'

            if state in [service_pb2.TicketState.Rejected, service_pb2.TicketState.Closed]:
                await reply(
                    self.websocket, AskResponse(
                        type=AskResponseType.waiting,
                        conversation_id=self.session.id,
                        system_message=system_message
                    )
                )
                break

            await asyncio.sleep(self.WAIT_TICKET_INTERVAL)

        if not ticket_closed:
            self.close_ticket(ticket_info)

        return is_continue

    async def command_acl_filter(self):
        is_continue = True
        acl = await self.match_rule()
        if acl is not None:
            if acl.action == CommandACL.Reject:
                is_continue = False
                self.command_record.risk_level = RiskLevel.Reject
                await reply(
                    self.websocket, AskResponse(
                        type=AskResponseType.reject,
                        conversation_id=self.session.id,
                        system_message='The conversation has been rejected'
                    )
                )
            elif acl.action == CommandACL.Review:
                is_continue = False
                start_time = time.time()
                end_time = start_time + 60
                await reply(
                    self.websocket, AskResponse(
                        type=AskResponseType.waiting,
                        conversation_id=self.session.id,
                        system_message=
                        'You need to review the command before it can be executed. '
                        'Do you want to initiate a review request?',
                        meta=ResponseMeta(activate_review=True)
                    )
                )

                while time.time() <= end_time:
                    if self.jms_state.activate_review is None:
                        await asyncio.sleep(1)
                        continue
                    if self.jms_state.activate_review:
                        self.jms_state.activate_review = None
                        is_continue = await self.create_and_wait_ticket(acl)
                        break
                    else:
                        self.jms_state.activate_review = None
                        is_continue = False
                        break
            elif acl.action == CommandACL.Warning:
                self.command_record.risk_level = RiskLevel.Warning
        return is_continue

    def close_ticket(self, ticket_info: service_pb2.TicketInfo):
        req = service_pb2.TicketRequest(req=ticket_info.cancel_req)
        resp = self.stub.CancelTicket(req)
        if not resp.status.ok:
            error_message = f'Failed to close ticket: {resp.status.err}'
            logger.error(error_message)
