"""
Taskmarket requester tools for Open WebUI.

Lets a chat assistant create a funded Taskmarket task on Base Mainnet as the
requester, fetch its live status, and list submissions for human review.

Safety contract:

- The full task configuration is validated locally before any CLI call, so a
  misconfigured task can never reach the network.
- Task creation first returns the exact task that will be created
  (description, reward, deadline, deliverables, Base network, max spend)
  together with a confirmation code bound to that exact configuration. The
  user must type that code back before any money moves; if any field changes
  between preview and confirmation, the code no longer matches and the tool
  refuses.
- Before every paid write the tool verifies that the configured backend
  reports Base Mainnet (chain id 8453, canonical USDC contract) and that the
  wallet balance covers the authorized max spend.
- A paid write that times out or reports an in-flight intent is never retried
  automatically; the error tells the caller to re-check the task status
  instead.
- The first-party ``taskmarket`` CLI owns the wallet, signatures, legal
  receipts, and the X402 payment flow. This module only spawns the CLI and
  parses its JSON envelopes; no private keys, seed phrases, tokens, or
  cookies are requested, stored, or logged.
"""

import asyncio
import hashlib
import logging
import os
import re
from typing import Optional

from open_webui.utils.json_codec import JSONCodec

log = logging.getLogger(__name__)

# Base Mainnet chain id and USDC contract used by Taskmarket production.
# See https://docs.taskmarket.dev/reference/network for the canonical table.
TASKMARKET_BASE_CHAIN_ID = 8453
TASKMARKET_BASE_USDC_CONTRACT = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
TASKMARKET_BASE_NETWORK_NAME = 'Base Mainnet'
TASKMARKET_WEB_ROOT = 'https://taskmarket.dev'

ETH_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')
TASK_ID_RE = re.compile(r'^0x[0-9a-fA-F]{64}$')

# Per-invocation timeouts in seconds. Paid writes settle two on-chain
# transactions through the x402 flow, so they get a longer budget.
CLI_TIMEOUT_S = 60
CREATE_TIMEOUT_S = 120


class TaskmarketValidationError(Exception):
    """The task configuration failed local validation; nothing was sent."""


class TaskmarketAuthorizationError(Exception):
    """The explicit confirmation code was missing, stale, or mismatched."""


class TaskmarketNetworkError(Exception):
    """The configured backend is not Taskmarket production on Base Mainnet."""


class TaskmarketFundingError(Exception):
    """The wallet balance does not cover the authorized max spend."""


class TaskmarketCliError(Exception):
    """The Taskmarket CLI failed, timed out, or returned unparsable output.

    ``timed_out`` marks an ambiguous outcome: the paid write may still be
    settling on-chain and must never be retried automatically.
    """

    def __init__(
        self,
        message,
        *,
        exit_code=None,
        status=None,
        idempotency_key=None,
        pending=None,
        reason=None,
        intent_id=None,
        timed_out=False,
    ):
        super().__init__(message)
        self.exit_code = exit_code
        self.status = status
        self.idempotency_key = idempotency_key
        self.pending = pending
        self.reason = reason
        self.intent_id = intent_id
        self.timed_out = timed_out


def usdc_to_base_units(raw):
    """Converts a human-readable USDC amount (at most 6 decimal places) to base units."""
    match = re.match(r'^(\d+)(?:\.(\d{1,6}))?$', str(raw).strip())
    if match is None:
        raise TaskmarketValidationError(f'Invalid USDC amount: "{raw}"')
    whole = int(match.group(1))
    fraction = (match.group(2) or '').ljust(6, '0')
    fraction_units = int(fraction) if fraction else 0
    return whole * 1_000_000 + fraction_units


def is_task_id(value):
    """True when ``value`` looks like a 0x-prefixed 32-byte task id."""
    return bool(value) and bool(TASK_ID_RE.match(str(value)))


def is_task_open(task):
    """True when the task is open and actively accepting submissions."""
    return task.get('status') == 'open' and (task.get('phase') is None or task.get('phase') == 'active')


def task_status_line(task):
    """Compact one-line status summary used after creation."""
    status = task.get('status') or 'unknown'
    phase = task.get('phase')
    submissions = task.get('submissionCount') or 0
    return f'status={status} phase={phase if phase is not None else "n/a"} submissions={submissions}'


def taskmarket_task_url(task_id):
    """Public Taskmarket page for a task."""
    return f'{TASKMARKET_WEB_ROOT}/tasks/{task_id}'


def _assert_usdc_amount(raw, label):
    trimmed = str(raw).strip()
    match = re.match(r'^(\d{1,9})(?:\.(\d{1,6}))?$', trimmed)
    if match is None:
        raise TaskmarketValidationError(
            f'{label} must be a USDC amount with at most 6 decimal places (e.g. 5 or 5.5), got "{raw}"'
        )
    if float(trimmed) <= 0:
        raise TaskmarketValidationError(f'{label} must be greater than zero, got "{raw}"')
    return trimmed


def _assert_positive_hours(raw, label):
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not raw > 0:
        raise TaskmarketValidationError(f'{label} must be a positive number of hours, got {raw}')


def _assert_address_list(raw, label):
    for address in raw:
        if not ETH_ADDRESS_RE.match(str(address)):
            raise TaskmarketValidationError(f'{label} contains an invalid Ethereum address: "{address}"')


def _normalize_tags(raw):
    tags = []
    for tag in raw or []:
        tag = str(tag).strip()
        if tag:
            tags.append(tag)
    return tags[:10]


def validate_create_config(raw):
    """Validates a task-creation configuration and returns (config, cli_args).

    All validation happens locally before any CLI call, so a misconfigured
    task can never reach the network. ``maxSpendUsdc`` is the
    user-authorized spending cap: the Taskmarket CLI escrows exactly
    ``rewardUsdc`` on creation (the platform fee is deducted from the reward
    when workers are paid, never charged on top), so the cap must equal or
    exceed the reward; the cap is surfaced in the preview and enforced by the
    balance guard.
    """
    description = str(raw.get('description') or '').strip()
    if len(description) < 10:
        raise TaskmarketValidationError('description must be at least 10 characters')
    if len(description) > 4000:
        raise TaskmarketValidationError('description must be at most 4000 characters')

    reward_usdc = _assert_usdc_amount(raw.get('rewardUsdc'), 'reward')
    _assert_positive_hours(raw.get('durationHours'), 'duration')
    duration_hours = raw.get('durationHours')

    mode = raw.get('mode')
    if mode not in ('bounty', 'claim', 'pitch', 'benchmark', 'auction'):
        raise TaskmarketValidationError(f'mode must be one of bounty, claim, pitch, benchmark, auction; got "{mode}"')

    task_visibility = raw.get('taskVisibility')
    if task_visibility not in ('public', 'unlisted', 'private'):
        raise TaskmarketValidationError(
            f'taskVisibility must be one of public, unlisted, private; got "{task_visibility}"'
        )

    submission_visibility = raw.get('submissionVisibility')
    if submission_visibility not in ('public', 'reveal_all', 'winner_only', 'never'):
        raise TaskmarketValidationError(
            f'submissionVisibility must be one of public, reveal_all, winner_only, never; got "{submission_visibility}"'
        )

    max_spend_usdc = _assert_usdc_amount(raw.get('maxSpendUsdc'), 'maxSpend')
    if usdc_to_base_units(max_spend_usdc) < usdc_to_base_units(reward_usdc):
        raise TaskmarketValidationError(
            f'maxSpend ({max_spend_usdc} USDC) must be at least the reward ({reward_usdc} USDC)'
        )

    tags = _normalize_tags(raw.get('tags'))
    allowed_viewers = list(raw.get('allowedViewers') or [])
    _assert_address_list(allowed_viewers, 'allowedViewers')
    private_access_password = raw.get('privateAccessPassword')

    if task_visibility == 'private':
        if not allowed_viewers and not private_access_password:
            raise TaskmarketValidationError(
                'taskVisibility "private" requires at least one allowedViewers address or a privateAccessPassword'
            )
        if private_access_password is not None and len(str(private_access_password)) < 8:
            raise TaskmarketValidationError('privateAccessPassword must be at least 8 characters')
    elif allowed_viewers or private_access_password is not None:
        raise TaskmarketValidationError(
            'allowedViewers and privateAccessPassword are only valid with taskVisibility "private"'
        )

    max_price_usdc = None
    auction_type = None
    auction_start_price_usdc = None
    auction_floor_price_usdc = None

    if mode == 'auction':
        auction_type = raw.get('auctionType')
        if auction_type is None:
            raise TaskmarketValidationError('auction mode requires an auctionType')
        if auction_type not in ('dutch', 'english', 'reverse_dutch', 'reverse_english'):
            raise TaskmarketValidationError(
                f'auctionType must be one of dutch, english, reverse_dutch, reverse_english; got "{auction_type}"'
            )
        if raw.get('maxPriceUsdc') is None:
            raise TaskmarketValidationError('auction mode requires maxPrice')
        max_price_usdc = _assert_usdc_amount(raw.get('maxPriceUsdc'), 'maxPrice')
        if max_price_usdc != reward_usdc:
            raise TaskmarketValidationError(
                f'maxPrice ({max_price_usdc} USDC) must equal reward ({reward_usdc} USDC) for auction mode'
            )
        if auction_type == 'dutch':
            if raw.get('auctionFloorPriceUsdc') is None:
                raise TaskmarketValidationError('dutch auctions require auctionFloorPrice')
            auction_floor_price_usdc = _assert_usdc_amount(raw.get('auctionFloorPriceUsdc'), 'auctionFloorPrice')
            if usdc_to_base_units(auction_floor_price_usdc) > usdc_to_base_units(reward_usdc):
                raise TaskmarketValidationError(
                    f'auctionFloorPrice ({auction_floor_price_usdc} USDC) must not exceed reward ({reward_usdc} USDC)'
                )
        if auction_type == 'reverse_dutch':
            if raw.get('auctionStartPriceUsdc') is None:
                raise TaskmarketValidationError('reverse_dutch auctions require auctionStartPrice')
            auction_start_price_usdc = _assert_usdc_amount(raw.get('auctionStartPriceUsdc'), 'auctionStartPrice')
            if usdc_to_base_units(auction_start_price_usdc) > usdc_to_base_units(reward_usdc):
                raise TaskmarketValidationError(
                    f'auctionStartPrice ({auction_start_price_usdc} USDC) must not exceed reward ({reward_usdc} USDC)'
                )
        if raw.get('bidDeadlineHours') is not None:
            _assert_positive_hours(raw.get('bidDeadlineHours'), 'bidDeadline')
    elif (
        raw.get('maxPriceUsdc') is not None
        or raw.get('auctionType') is not None
        or raw.get('auctionStartPriceUsdc') is not None
        or raw.get('auctionFloorPriceUsdc') is not None
        or raw.get('bidDeadlineHours') is not None
    ):
        raise TaskmarketValidationError('auction-only fields require mode "auction"')

    if mode == 'pitch' and raw.get('pitchDeadlineHours') is not None:
        _assert_positive_hours(raw.get('pitchDeadlineHours'), 'pitchDeadline')
    elif mode != 'pitch' and raw.get('pitchDeadlineHours') is not None:
        raise TaskmarketValidationError('pitchDeadline is only valid for pitch mode')

    config = {
        'description': description,
        'rewardUsdc': reward_usdc,
        'durationHours': duration_hours,
        'mode': mode,
        'taskVisibility': task_visibility,
        'submissionVisibility': submission_visibility,
        'maxSpendUsdc': max_spend_usdc,
        'tags': tags,
        'privateAccessPassword': private_access_password,
        'allowedViewers': allowed_viewers,
        'maxPriceUsdc': max_price_usdc,
        'auctionType': auction_type,
        'auctionStartPriceUsdc': auction_start_price_usdc,
        'auctionFloorPriceUsdc': auction_floor_price_usdc,
        'pitchDeadlineHours': raw.get('pitchDeadlineHours'),
        'bidDeadlineHours': raw.get('bidDeadlineHours'),
    }

    args = [
        '--description',
        description,
        '--reward',
        reward_usdc,
        '--duration',
        str(duration_hours),
        '--mode',
        mode,
        '--task-visibility',
        task_visibility,
        '--submission-visibility',
        submission_visibility,
    ]
    if tags:
        args.extend(['--tags', ','.join(tags)])
    if task_visibility == 'private':
        if allowed_viewers:
            args.extend(['--allowed-viewers', ','.join(allowed_viewers)])
        if private_access_password is not None:
            args.extend(['--access-password', str(private_access_password)])
    if mode == 'auction':
        args.extend(['--auction-type', auction_type, '--max-price', max_price_usdc])
        if auction_floor_price_usdc is not None:
            args.extend(['--auction-floor-price', auction_floor_price_usdc])
        if auction_start_price_usdc is not None:
            args.extend(['--auction-start-price', auction_start_price_usdc])
        if raw.get('bidDeadlineHours') is not None:
            args.extend(['--bid-deadline', str(raw.get('bidDeadlineHours'))])
    if mode == 'pitch' and raw.get('pitchDeadlineHours') is not None:
        args.extend(['--pitch-deadline', str(raw.get('pitchDeadlineHours'))])

    return config, args


def build_confirmation_code(config):
    """Derives the confirmation code bound to this exact task configuration.

    The code is a short digest over every field that will be sent to
    Taskmarket, so showing a preview and confirming it authorizes precisely
    that task and nothing else. If any field changes between preview and
    confirmation, the code no longer matches and the authorization gate
    refuses to create.
    """
    canonical = JSONCodec.dumps(
        {
            'description': config['description'],
            'rewardUsdc': config['rewardUsdc'],
            'durationHours': config['durationHours'],
            'mode': config['mode'],
            'taskVisibility': config['taskVisibility'],
            'submissionVisibility': config['submissionVisibility'],
            'maxSpendUsdc': config['maxSpendUsdc'],
            'tags': config['tags'],
            'privateAccessPassword': config.get('privateAccessPassword'),
            'allowedViewers': config.get('allowedViewers') or [],
            'maxPriceUsdc': config.get('maxPriceUsdc'),
            'auctionType': config.get('auctionType'),
            'auctionStartPriceUsdc': config.get('auctionStartPriceUsdc'),
            'auctionFloorPriceUsdc': config.get('auctionFloorPriceUsdc'),
            'pitchDeadlineHours': config.get('pitchDeadlineHours'),
            'bidDeadlineHours': config.get('bidDeadlineHours'),
        }
    )
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return f'tm-{digest[:12]}'


def build_create_preview(config):
    """Renders the exact task the user is about to create.

    Includes the network, the maximum spend cap, and the escrow mechanics.
    Everything shown here is what the authorization gate commits to.
    """
    preview = {
        'description': config['description'],
        'rewardUsdc': config['rewardUsdc'],
        'durationHours': config['durationHours'],
        'mode': config['mode'],
        'network': TASKMARKET_BASE_NETWORK_NAME,
        'chainId': TASKMARKET_BASE_CHAIN_ID,
        'usdcContract': TASKMARKET_BASE_USDC_CONTRACT,
        'maxSpendUsdc': config['maxSpendUsdc'],
        'taskVisibility': config['taskVisibility'],
        'submissionVisibility': config['submissionVisibility'],
        'tags': config['tags'],
        'privateAccessPasswordSet': config.get('privateAccessPassword') is not None,
        'allowedViewers': config.get('allowedViewers') or [],
        'confirmationCode': build_confirmation_code(config),
    }
    for key in (
        'maxPriceUsdc',
        'auctionType',
        'auctionStartPriceUsdc',
        'auctionFloorPriceUsdc',
        'pitchDeadlineHours',
        'bidDeadlineHours',
    ):
        if config.get(key) is not None:
            preview[key] = config[key]
    return preview


def authorize_task_creation(preview, confirm, rendered_code):
    """Authorization gate: requires the exact code bound to the preview.

    A missing, stale, or mismatched code aborts before any CLI call. The gate
    also refuses to authorize a max spend below the escrowed reward, which
    would be a lie about the money that moves.
    """
    if confirm != rendered_code:
        raise TaskmarketAuthorizationError(
            'Authorization required: pass the exact confirmation code shown with the task preview to create and fund this task. No task was created.'
        )
    if usdc_to_base_units(preview['maxSpendUsdc']) < usdc_to_base_units(preview['rewardUsdc']):
        raise TaskmarketAuthorizationError(
            f'Authorization refused: maxSpend ({preview["maxSpendUsdc"]} USDC) is below the escrowed reward ({preview["rewardUsdc"]} USDC).'
        )


class TaskmarketClient:
    """Runs the first-party Taskmarket CLI and parses its JSON envelopes.

    The CLI prints ``{"ok": true, "data": ...}`` on stdout for success and
    ``{"ok": false, "error": ...}`` (with optional ``status``,
    ``idempotencyKey``, ``pending``, ``reason``, ``intentId``) on stderr with
    exit code 1. The CLI owns the wallet, signatures, artifact uploads,
    legal-acceptance receipts, and the x402 payment flow; this client never
    touches keys.
    """

    def __init__(self, cli_path=None, timeout_s=None):
        self.cli_path = cli_path or os.getenv('TASKMARKET_CLI_PATH') or 'taskmarket'
        self.timeout_s = timeout_s or CLI_TIMEOUT_S

    @staticmethod
    def _last_envelope(lines):
        for line in reversed(lines):
            line = line.strip()
            if not line.startswith('{'):
                continue
            try:
                parsed = JSONCodec.loads(line)
            except ValueError:
                continue
            if isinstance(parsed, dict) and 'ok' in parsed:
                return parsed
        return None

    async def run(self, args, timeout_s=None):
        """Runs the CLI and returns ``(data, idempotency_key)`` on success."""
        timeout = timeout_s or self.timeout_s
        try:
            process = await asyncio.create_subprocess_exec(
                self.cli_path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise TaskmarketCliError(
                f'Taskmarket CLI not found at "{self.cli_path}". Install the first-party CLI with '
                '`npm install -g @lucid-agents/taskmarket` and run `taskmarket init` to create the agent wallet.'
            )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TaskmarketCliError(
                f'taskmarket {" ".join(args)} timed out after {timeout}s; the outcome is unknown and may still '
                'be settling on-chain - do not retry automatically, re-check the task status instead',
                timed_out=True,
            )

        stdout = stdout_bytes.decode('utf-8', 'replace')
        stderr = stderr_bytes.decode('utf-8', 'replace')
        stdout_lines = stdout.splitlines()
        stderr_lines = stderr.splitlines()

        success = self._last_envelope(stdout_lines)
        if success is not None and success.get('ok') is True:
            return success.get('data'), success.get('idempotencyKey')

        failure = self._last_envelope(stderr_lines) or self._last_envelope(stdout_lines)
        if failure is not None and failure.get('ok') is False:
            details = ''
            if failure.get('status') is not None:
                details = f' (status {failure.get("status")})'
            elif failure.get('idempotencyKey') is not None:
                details = f' (idempotencyKey {failure.get("idempotencyKey")})'
            pending_hint = ''
            if failure.get('pending') is True:
                pending_hint = ' The write is still in flight and may succeed; re-check status before any retry.'
            raise TaskmarketCliError(
                f'taskmarket {" ".join(args)} failed{details}: {failure.get("error")}{pending_hint}',
                exit_code=process.returncode,
                status=failure.get('status'),
                idempotency_key=failure.get('idempotencyKey'),
                pending=failure.get('pending'),
                reason=failure.get('reason'),
                intent_id=failure.get('intentId'),
            )

        stderr_tail = stderr.strip()[:500]
        raise TaskmarketCliError(
            f'taskmarket {" ".join(args)} exited with code {process.returncode} without a parsable JSON envelope'
            + (f': {stderr_tail}' if stderr_tail else ''),
            exit_code=process.returncode,
        )

    async def deposit(self):
        data, _ = await self.run(['deposit'])
        return data or {}

    async def balance(self):
        data, _ = await self.run(['wallet', 'balance'])
        return data or {}

    async def get_task(self, task_id):
        data, _ = await self.run(['task', 'get', task_id])
        return data or {}

    async def submissions(self, task_id):
        data, _ = await self.run(['task', 'submissions', task_id])
        return data or []

    async def create_task(self, create_args):
        """Creates a task. ``create_args`` come from the validation layer.

        The write is paid (the reward amount in USDC is escrowed) and may take
        a while because the x402 flow settles two on-chain transactions.
        """
        data, idempotency_key = await self.run(['task', 'create', *create_args], timeout_s=CREATE_TIMEOUT_S)
        task_id = data.get('taskId') if isinstance(data, dict) else None
        if not isinstance(task_id, str):
            suffix = f' (idempotencyKey {idempotency_key})' if idempotency_key is not None else ''
            raise TaskmarketCliError(
                f'taskmarket task create returned no taskId{suffix}', idempotency_key=idempotency_key
            )
        return {'taskId': task_id, 'idempotencyKey': idempotency_key}


async def assert_base_network(client):
    """Network guard: refuses any backend that is not production Base Mainnet.

    ``taskmarket deposit`` reports the network, chain id, and USDC contract of
    the configured backend (selected by ``TASKMARKET_API_URL`` or production
    by default).
    """
    try:
        deposit = await client.deposit()
    except TaskmarketCliError as error:
        raise TaskmarketNetworkError(f'Cannot verify the Taskmarket network before this action: {error}') from error
    if deposit.get('chainId') != TASKMARKET_BASE_CHAIN_ID or deposit.get('network') != 'Base':
        raise TaskmarketNetworkError(
            f'Refusing to act: the configured Taskmarket backend reports network "{deposit.get("network")}" '
            f'(chain id {deposit.get("chainId")}), but this integration only operates on '
            f'{TASKMARKET_BASE_NETWORK_NAME} (chain id {TASKMARKET_BASE_CHAIN_ID}). Set TASKMARKET_API_URL '
            'back to the production backend (or unset it) and re-run.'
        )
    if str(deposit.get('usdcContract') or '').lower() != TASKMARKET_BASE_USDC_CONTRACT.lower():
        raise TaskmarketNetworkError(
            f'Refusing to act: the configured Taskmarket backend reports USDC contract '
            f'{deposit.get("usdcContract")}, expected {TASKMARKET_BASE_USDC_CONTRACT} on '
            f'{TASKMARKET_BASE_NETWORK_NAME}.'
        )
    return deposit


async def assert_sufficient_balance(client, max_spend_usdc):
    """Spending guard: the wallet must hold at least the full max spend.

    The wallet must be funded with Base Mainnet USDC; the CLI escrows the
    reward on task creation.
    """
    max_spend_base_units = usdc_to_base_units(max_spend_usdc)
    balance = await client.balance()
    balance_base_units = int(balance.get('balanceBaseUnits') or 0)
    if balance_base_units < max_spend_base_units:
        raise TaskmarketFundingError(
            f'Insufficient USDC: the wallet {balance.get("address")} holds {balance.get("balanceUsdc")} USDC '
            f'but this task requires up to {max_spend_usdc} USDC (reward plus fees). Fund the wallet on '
            f'{TASKMARKET_BASE_NETWORK_NAME} and re-run.'
        )
    return {'address': balance.get('address'), 'balanceUsdc': balance.get('balanceUsdc')}


def _error_json(error):
    return JSONCodec.dumps({'error': str(error)}, ensure_ascii=False)


async def taskmarket_create_task(
    description: str,
    reward_usdc: str,
    duration_hours: int,
    max_spend_usdc: str,
    mode: str = 'bounty',
    task_visibility: str = 'public',
    submission_visibility: str = 'public',
    tags: Optional[list[str]] = None,
    private_access_password: str = '',
    allowed_viewers: Optional[list[str]] = None,
    max_price_usdc: str = '',
    auction_type: str = '',
    auction_start_price_usdc: str = '',
    auction_floor_price_usdc: str = '',
    bid_deadline_hours: int = 0,
    pitch_deadline_hours: int = 0,
    confirm: str = '',
) -> str:
    """
    Create a funded Taskmarket task on Base Mainnet as the requester, escrowing the reward in USDC. Paid action with a two-step authorization flow: on the first call (without confirm) this tool returns the exact task preview - description, reward, deadline (duration), deliverables (mode and submission visibility), Base network, and max spend - together with a confirmation code bound to that exact task. Show the preview to the user and ask them to type the confirmation code back. On the second call, pass the SAME task fields with confirm set to that code; any change to the task between preview and confirmation invalidates the code and the tool refuses. Never call this tool with confirm unless the user has explicitly typed the code shown in the preview. Before creating, the tool verifies the backend is Base Mainnet and the wallet balance covers the max spend.

    :param description: Task description shown to workers. Be specific about the work, deliverables, and acceptance criteria
    :param reward_usdc: Reward in USDC escrowed on Base Mainnet (e.g. "25" or "25.5")
    :param duration_hours: Task duration in hours; the submission window closes at the deadline
    :param max_spend_usdc: Maximum spend you authorize for this task in USDC; the wallet balance must cover it, and for the standard bounty flow set it equal to the reward (the exact amount escrowed)
    :param mode: Task mode: bounty (any worker submits), claim (one worker claims), pitch, benchmark, or auction
    :param task_visibility: Who can view the task: public, unlisted, or private (private requires allowed_viewers or an access password)
    :param submission_visibility: Who can see submissions after the task ends: public, reveal_all, winner_only, or never (locked in permanently at creation)
    :param tags: Comma-separated topic tags (max 10) that help workers find the task
    :param private_access_password: Password (min 8 chars) granting anonymous access to a private task; only valid with task_visibility private
    :param allowed_viewers: Wallet addresses invited to view a private task; only valid with task_visibility private
    :param max_price_usdc: Auction mode only; must equal reward_usdc (the escrowed maximum)
    :param auction_type: Auction mode only: dutch, english, reverse_dutch, or reverse_english
    :param auction_start_price_usdc: reverse_dutch only: starting clock price, at most the reward
    :param auction_floor_price_usdc: dutch only: floor price, at most the reward
    :param bid_deadline_hours: Auction mode only: bid deadline in hours from now
    :param pitch_deadline_hours: Pitch mode only: pitch deadline in hours from now
    :param confirm: Explicit authorization; pass the exact confirmation code returned by the preview step. A task is never created without it
    :return: JSON with the exact task preview and confirmation code (first call), or the created task id, link, idempotency key, wallet address, and live status (confirmed call)
    """
    raw = {
        'description': description,
        'rewardUsdc': reward_usdc,
        'durationHours': duration_hours,
        'mode': mode,
        'taskVisibility': task_visibility,
        'submissionVisibility': submission_visibility,
        'maxSpendUsdc': max_spend_usdc,
        'tags': tags or [],
    }
    if private_access_password:
        raw['privateAccessPassword'] = private_access_password
    if allowed_viewers:
        raw['allowedViewers'] = allowed_viewers
    if mode == 'auction':
        if max_price_usdc:
            raw['maxPriceUsdc'] = max_price_usdc
        if auction_type:
            raw['auctionType'] = auction_type
        if auction_start_price_usdc:
            raw['auctionStartPriceUsdc'] = auction_start_price_usdc
        if auction_floor_price_usdc:
            raw['auctionFloorPriceUsdc'] = auction_floor_price_usdc
        if bid_deadline_hours and bid_deadline_hours > 0:
            raw['bidDeadlineHours'] = bid_deadline_hours
    if mode == 'pitch' and pitch_deadline_hours and pitch_deadline_hours > 0:
        raw['pitchDeadlineHours'] = pitch_deadline_hours

    try:
        config, args = validate_create_config(raw)
        preview = build_create_preview(config)

        if not confirm:
            return JSONCodec.dumps(
                {
                    'status': 'preview_required',
                    'instruction': (
                        'Review the exact task above (description, reward, deadline, deliverables, '
                        'Base network, max spend). To create and fund it, call this tool again with the '
                        'SAME task fields and confirm set to the confirmation code. No task is created '
                        'without it.'
                    ),
                    **preview,
                },
                ensure_ascii=False,
            )

        # Authorization gate: the confirmation code is bound to this exact
        # task. A missing, stale, or mismatched code aborts before any CLI call.
        authorize_task_creation(preview, confirm, preview['confirmationCode'])

        client = TaskmarketClient()

        # Network guard: refuse anything that is not production Base.
        await assert_base_network(client)

        # Spending guard: wallet must cover the authorized max spend.
        wallet = await assert_sufficient_balance(client, preview['maxSpendUsdc'])

        result = await client.create_task(args)
    except (
        TaskmarketValidationError,
        TaskmarketAuthorizationError,
        TaskmarketNetworkError,
        TaskmarketFundingError,
        TaskmarketCliError,
    ) as error:
        return _error_json(error)
    except Exception as error:
        log.exception('taskmarket_create_task error: %s', error)
        return _error_json(error)

    task_id = result['taskId']
    status = 'created'
    try:
        task = await client.get_task(task_id)
        status = task_status_line(task)
    except Exception:
        # The task id is the source of truth; status refresh is best-effort.
        pass

    return JSONCodec.dumps(
        {
            'status': 'created',
            'taskId': task_id,
            'taskUrl': taskmarket_task_url(task_id),
            'idempotencyKey': result.get('idempotencyKey'),
            'walletAddress': wallet['address'],
            'taskStatus': status,
        },
        ensure_ascii=False,
    )


async def taskmarket_task_status(task_id: str) -> str:
    """
    Fetch the live status of a Taskmarket task by id: status, phase, reward, net reward, platform fee, expiry, submission window, and submission count. Read-only; costs nothing and never changes state.

    :param task_id: The 0x-prefixed 32-byte task id returned by taskmarket_create_task
    :return: JSON with taskId, taskUrl, status, phase, reward, netReward, platformFeeBps, expiryTime, submissionWindowOpen, submissionCount, requester
    """
    try:
        client = TaskmarketClient()
        task = await client.get_task(task_id)
        return JSONCodec.dumps(
            {
                'taskId': task.get('id') or task_id,
                'taskUrl': taskmarket_task_url(task.get('id') or task_id),
                'status': task.get('status') or 'unknown',
                'phase': task.get('phase'),
                'reward': task.get('reward'),
                'netReward': task.get('netReward'),
                'platformFeeBps': task.get('platformFeeBps'),
                'expiryTime': task.get('expiryTime'),
                'submissionWindowOpen': task.get('submissionWindowOpen'),
                'submissionCount': task.get('submissionCount') or 0,
                'requester': task.get('requester'),
            },
            ensure_ascii=False,
        )
    except Exception as error:
        log.exception('taskmarket_task_status error: %s', error)
        return _error_json(error)


async def taskmarket_submissions(task_id: str) -> str:
    """
    List the submissions of a Taskmarket task (worker, timestamps, deliverable hash, tx hash) for human review. Read-only. Submissions are never accepted or rejected automatically; a human decides.

    :param task_id: The 0x-prefixed 32-byte task id returned by taskmarket_create_task
    :return: JSON with taskId, submissionCount, submissions, and a review instruction
    """
    try:
        client = TaskmarketClient()
        submissions = await client.submissions(task_id)
        return JSONCodec.dumps(
            {
                'taskId': task_id,
                'submissionCount': len(submissions),
                'submissions': [
                    {
                        'id': submission.get('id'),
                        'workerAddress': submission.get('workerAddress'),
                        'workerAgentId': submission.get('workerAgentId'),
                        'submittedAt': submission.get('submittedAt'),
                        'rejectedAt': submission.get('rejectedAt'),
                        'deliverableHash': submission.get('deliverableHash'),
                        'submitTxHash': submission.get('submitTxHash'),
                    }
                    for submission in submissions
                ],
                'reviewInstruction': (
                    'Review these submissions with a human before deciding anything. '
                    'This integration never accepts or rejects work automatically.'
                ),
            },
            ensure_ascii=False,
        )
    except Exception as error:
        log.exception('taskmarket_submissions error: %s', error)
        return _error_json(error)
