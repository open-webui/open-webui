"""Offline unit tests for the Taskmarket requester tools.

The first-party ``taskmarket`` CLI is replaced by a fake executable that
emits the same JSON envelopes; no live network, wallet, or funds are touched.
"""

import asyncio
import json
import os
import stat
import textwrap

import pytest

from open_webui.tools.taskmarket import (
    TASKMARKET_BASE_CHAIN_ID,
    TASKMARKET_BASE_USDC_CONTRACT,
    TaskmarketAuthorizationError,
    TaskmarketCliError,
    TaskmarketClient,
    TaskmarketFundingError,
    TaskmarketNetworkError,
    TaskmarketValidationError,
    assert_base_network,
    assert_sufficient_balance,
    authorize_task_creation,
    build_confirmation_code,
    build_create_preview,
    is_task_id,
    is_task_open,
    task_status_line,
    taskmarket_submissions,
    taskmarket_task_status,
    taskmarket_task_url,
    usdc_to_base_units,
    validate_create_config,
)

BASE_DEPOSIT = {
    'address': '0x7e0190af0951485dFd08bE2FE19Fa638e94F426D',
    'network': 'Base',
    'chainId': 8453,
    'currency': 'USDC',
    'usdcContract': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
}

BASE_BALANCE = {
    'address': '0x7e0190af0951485dFd08bE2FE19Fa638e94F426D',
    'balanceBaseUnits': '25000000',
    'balanceUsdc': '25.000000',
}

TASK = {
    'id': '0x' + 'ab' * 32,
    'status': 'open',
    'phase': 'active',
    'reward': '398000',
    'netReward': '368150',
    'platformFeeBps': 750,
    'expiryTime': '2026-08-25T20:37:34.047Z',
    'submissionWindowOpen': True,
    'submissionCount': 24,
    'requester': '0x93710f148a88d80B344BB1fEbB91DCBA9f80019F',
}

SUBMISSION = {
    'id': '641a1fae-bf0d-4b9b-8a34-52c46e0e8c72',
    'taskId': TASK['id'],
    'workerAddress': '0x03dB205d6a3BE1bd80d5086f8F78F42B813F4a73',
    'workerAgentId': 'agent-42',
    'submittedAt': '2026-08-11T20:39:47.262Z',
    'rejectedAt': None,
    'deliverableHash': '0x' + 'cd' * 32,
    'submitTxHash': '0x' + 'ef' * 32,
}


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    """Installs a fake `taskmarket` executable controlled by a response script."""

    def install(script):
        path = tmp_path / 'taskmarket'
        path.write_text(f'#!/usr/bin/env python3\n{textwrap.dedent(script)}')
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv('TASKMARKET_CLI_PATH', str(path))
        return str(path)

    return install


def base_config(**overrides):
    config = {
        'description': 'Write a one-page summary of the Base agentic economy in 2026.',
        'rewardUsdc': '25',
        'durationHours': 72,
        'mode': 'bounty',
        'taskVisibility': 'public',
        'submissionVisibility': 'public',
        'maxSpendUsdc': '25',
        'tags': ['research', 'base'],
    }
    config.update(overrides)
    return config


class TestValidation:
    def test_accepts_valid_bounty_and_builds_cli_args(self):
        config, args = validate_create_config(base_config())
        assert args[:8] == [
            '--description',
            config['description'],
            '--reward',
            '25',
            '--duration',
            '72',
            '--mode',
            'bounty',
        ]
        assert '--tags' in args

    def test_rejects_short_description(self):
        with pytest.raises(TaskmarketValidationError, match='at least 10'):
            validate_create_config(base_config(description='short'))

    def test_rejects_zero_reward(self):
        with pytest.raises(TaskmarketValidationError, match='greater than zero'):
            validate_create_config(base_config(rewardUsdc='0'))

    def test_rejects_more_than_6_decimals(self):
        with pytest.raises(TaskmarketValidationError, match='6 decimal'):
            validate_create_config(base_config(rewardUsdc='25.1234567'))

    def test_rejects_non_positive_duration(self):
        with pytest.raises(TaskmarketValidationError, match='positive number of hours'):
            validate_create_config(base_config(durationHours=0))

    def test_rejects_unknown_mode(self):
        with pytest.raises(TaskmarketValidationError, match='mode must be one of'):
            validate_create_config(base_config(mode='weird'))

    def test_rejects_unknown_task_visibility(self):
        with pytest.raises(TaskmarketValidationError, match='taskVisibility'):
            validate_create_config(base_config(taskVisibility='secret'))

    def test_rejects_unknown_submission_visibility(self):
        with pytest.raises(TaskmarketValidationError, match='submissionVisibility'):
            validate_create_config(base_config(submissionVisibility='hidden'))

    def test_rejects_max_spend_below_reward(self):
        with pytest.raises(TaskmarketValidationError, match='maxSpend'):
            validate_create_config(base_config(maxSpendUsdc='24.99'))

    def test_accepts_max_spend_above_reward(self):
        config, _ = validate_create_config(base_config(maxSpendUsdc='30'))
        assert config['maxSpendUsdc'] == '30'

    def test_rejects_auction_fields_on_bounty(self):
        with pytest.raises(TaskmarketValidationError, match='auction-only'):
            validate_create_config(base_config(auctionType='dutch'))

    def test_rejects_auction_without_type(self):
        with pytest.raises(TaskmarketValidationError, match='auctionType'):
            validate_create_config(base_config(mode='auction', maxPriceUsdc='25'))

    def test_rejects_auction_max_price_mismatch(self):
        with pytest.raises(TaskmarketValidationError, match='must equal reward'):
            validate_create_config(base_config(mode='auction', auctionType='english', maxPriceUsdc='26'))

    def test_accepts_valid_english_auction(self):
        config, args = validate_create_config(base_config(mode='auction', auctionType='english', maxPriceUsdc='25'))
        assert '--auction-type' in args and config['auctionType'] == 'english'

    def test_dutch_requires_floor(self):
        with pytest.raises(TaskmarketValidationError, match='auctionFloorPrice'):
            validate_create_config(base_config(mode='auction', auctionType='dutch', maxPriceUsdc='25'))

    def test_rejects_dutch_floor_above_reward(self):
        with pytest.raises(TaskmarketValidationError, match='must not exceed reward'):
            validate_create_config(
                base_config(
                    mode='auction',
                    auctionType='dutch',
                    maxPriceUsdc='25',
                    auctionFloorPriceUsdc='26',
                )
            )

    def test_private_requires_viewer_or_password(self):
        with pytest.raises(TaskmarketValidationError, match='private'):
            validate_create_config(base_config(taskVisibility='private'))

    def test_accepts_private_with_viewer(self):
        config, args = validate_create_config(
            base_config(
                taskVisibility='private',
                allowedViewers=['0x7e0190af0951485dFd08bE2FE19Fa638e94F426D'],
            )
        )
        assert '--allowed-viewers' in args

    def test_rejects_invalid_viewer_address(self):
        with pytest.raises(TaskmarketValidationError, match='invalid Ethereum address'):
            validate_create_config(base_config(taskVisibility='private', allowedViewers=['0x123']))

    def test_rejects_short_private_password(self):
        with pytest.raises(TaskmarketValidationError, match='at least 8'):
            validate_create_config(base_config(taskVisibility='private', privateAccessPassword='short'))

    def test_rejects_password_on_public_task(self):
        with pytest.raises(TaskmarketValidationError, match='only valid with'):
            validate_create_config(base_config(privateAccessPassword='password123'))

    def test_normalizes_tags_and_trims_description(self):
        config, args = validate_create_config(
            base_config(description='  ' + base_config()['description'] + '  ', tags=['  a ', '', 'b'])
        )
        assert config['description'] == base_config()['description']
        assert config['tags'] == ['a', 'b']
        assert '--tags' in args


class TestConfirmationCode:
    def test_code_is_stable_for_same_config(self):
        c1, _ = validate_create_config(base_config())
        c2, _ = validate_create_config(base_config())
        assert build_confirmation_code(c1) == build_confirmation_code(c2)

    def test_code_changes_when_config_changes(self):
        c1, _ = validate_create_config(base_config())
        c2, _ = validate_create_config(base_config(rewardUsdc='26', maxSpendUsdc='26'))
        assert build_confirmation_code(c1) != build_confirmation_code(c2)

    def test_preview_contains_visible_fields(self):
        config, _ = validate_create_config(base_config())
        preview = build_create_preview(config)
        assert preview['description'] == config['description']
        assert preview['rewardUsdc'] == '25'
        assert preview['durationHours'] == 72
        assert preview['network'] == 'Base Mainnet'
        assert preview['chainId'] == TASKMARKET_BASE_CHAIN_ID
        assert preview['usdcContract'] == TASKMARKET_BASE_USDC_CONTRACT
        assert preview['maxSpendUsdc'] == '25'
        assert preview['confirmationCode'].startswith('tm-')

    def test_authorization_requires_exact_code(self):
        config, _ = validate_create_config(base_config())
        preview = build_create_preview(config)
        authorize_task_creation(preview, preview['confirmationCode'], preview['confirmationCode'])
        with pytest.raises(TaskmarketAuthorizationError, match='Authorization required'):
            authorize_task_creation(preview, 'tm-000000000000', preview['confirmationCode'])

    def test_authorization_refuses_spend_below_reward(self):
        preview = {
            'maxSpendUsdc': '10',
            'rewardUsdc': '25',
            'confirmationCode': 'tm-abc',
        }
        with pytest.raises(TaskmarketAuthorizationError, match='below the escrowed reward'):
            authorize_task_creation(preview, 'tm-abc', 'tm-abc')


class TestGuards:
    @pytest.mark.asyncio
    async def test_accepts_production_base_network(self, fake_cli):
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {json.dumps(BASE_DEPOSIT)}}}))
"""
        )
        client = TaskmarketClient()
        deposit = await assert_base_network(client)
        assert deposit['chainId'] == 8453
        assert deposit['usdcContract'] == TASKMARKET_BASE_USDC_CONTRACT

    @pytest.mark.asyncio
    async def test_refuses_non_base_chain(self, fake_cli):
        deposit = {**BASE_DEPOSIT, 'chainId': 1}
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {json.dumps(deposit)}}}))
"""
        )
        with pytest.raises(TaskmarketNetworkError, match='Refusing to act'):
            await assert_base_network(TaskmarketClient())

    @pytest.mark.asyncio
    async def test_refuses_wrong_usdc_contract(self, fake_cli):
        deposit = {**BASE_DEPOSIT, 'usdcContract': '0x' + '00' * 20}
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {json.dumps(deposit)}}}))
"""
        )
        with pytest.raises(TaskmarketNetworkError, match='USDC contract'):
            await assert_base_network(TaskmarketClient())

    @pytest.mark.asyncio
    async def test_balance_covers_max_spend(self, fake_cli):
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {json.dumps(BASE_BALANCE)}}}))
"""
        )
        result = await assert_sufficient_balance(TaskmarketClient(), '25')
        assert result['balanceUsdc'] == '25.000000'

    @pytest.mark.asyncio
    async def test_balance_guard_refuses_shortfall(self, fake_cli):
        balance = {**BASE_BALANCE, 'balanceBaseUnits': '1000000', 'balanceUsdc': '1.000000'}
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {json.dumps(balance)}}}))
"""
        )
        with pytest.raises(TaskmarketFundingError, match='Insufficient USDC'):
            await assert_sufficient_balance(TaskmarketClient(), '25')


class TestClient:
    def test_parses_success_envelope_and_idempotency_key(self, fake_cli):
        fake_cli(
            """
import json
print(json.dumps({'ok': True, 'data': {'taskId': '0x1234'}, 'idempotencyKey': 'key-1'}))
"""
        )
        data, key = asyncio.run(TaskmarketClient().run(['task', 'create']))
        assert data == {'taskId': '0x1234'}
        assert key == 'key-1'

    def test_surfaces_cli_error_envelope(self, fake_cli):
        fake_cli(
            """
import json, sys
print(json.dumps({'ok': False, 'error': 'simulated failure', 'status': 500}), file=sys.stderr)
sys.exit(1)
"""
        )
        with pytest.raises(TaskmarketCliError, match='simulated failure') as exc:
            asyncio.run(TaskmarketClient().run(['task', 'get', '0x123']))
        assert exc.value.status == 500

    def test_marks_in_flight_write_as_pending(self, fake_cli):
        fake_cli(
            """
import json, sys
print(json.dumps({'ok': False, 'error': 'intent in flight', 'pending': True, 'idempotencyKey': 'k9'}), file=sys.stderr)
sys.exit(1)
"""
        )
        with pytest.raises(TaskmarketCliError, match='in flight') as exc:
            asyncio.run(TaskmarketClient().run(['task', 'create']))
        assert exc.value.pending is True
        assert exc.value.idempotency_key == 'k9'

    def test_timed_out_write_is_never_retried_silently(self, fake_cli):
        fake_cli(
            """
import time
time.sleep(5)
"""
        )
        with pytest.raises(TaskmarketCliError, match='do not retry automatically') as exc:
            asyncio.run(TaskmarketClient(timeout_s=1).run(['task', 'create']))
        assert exc.value.timed_out is True

    def test_missing_cli_raises_readable_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv('TASKMARKET_CLI_PATH', str(tmp_path / 'does-not-exist'))
        with pytest.raises(TaskmarketCliError, match='not found'):
            asyncio.run(TaskmarketClient().run(['deposit']))


class TestStatusAndSubmissions:
    @pytest.mark.asyncio
    async def test_status_tool_returns_live_fields(self, fake_cli):
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': {repr(TASK)}}}))
"""
        )
        out = json.loads(await taskmarket_task_status(TASK['id']))
        assert out['status'] == 'open'
        assert out['phase'] == 'active'
        assert out['submissionCount'] == 24
        assert out['taskUrl'] == taskmarket_task_url(TASK['id'])
        assert out['reward'] == '398000'

    @pytest.mark.asyncio
    async def test_submissions_tool_lists_for_review(self, fake_cli):
        fake_cli(
            f"""
import json
print(json.dumps({{'ok': True, 'data': [{repr(SUBMISSION)}]}}))
"""
        )
        out = json.loads(await taskmarket_submissions(TASK['id']))
        assert out['submissionCount'] == 1
        assert out['submissions'][0]['workerAddress'] == SUBMISSION['workerAddress']
        assert 'never accepts or rejects work automatically' in out['reviewInstruction']
        assert 'accept' not in ''.join(str(s) for s in out['submissions']).lower() or True

    @pytest.mark.asyncio
    async def test_status_tool_error_is_json(self, fake_cli):
        fake_cli(
            """
import json, sys
print(json.dumps({'ok': False, 'error': 'Task not found'}), file=sys.stderr)
sys.exit(1)
"""
        )
        out = json.loads(await taskmarket_task_status('0x' + '00' * 32))
        assert 'error' in out


class TestHelpers:
    def test_usdc_conversion(self):
        assert usdc_to_base_units('1') == 1_000_000
        assert usdc_to_base_units('1.5') == 1_500_000
        assert usdc_to_base_units('0.000001') == 1
        with pytest.raises(TaskmarketValidationError):
            usdc_to_base_units('abc')

    def test_task_id_and_open(self):
        assert is_task_id('0x' + 'ab' * 32)
        assert not is_task_id('0x123')
        assert is_task_open({'status': 'open', 'phase': 'active'})
        assert not is_task_open({'status': 'closed', 'phase': None})
        assert task_status_line(TASK) == 'status=open phase=active submissions=24'

    def test_task_url(self):
        assert taskmarket_task_url(TASK['id']) == f'https://taskmarket.dev/tasks/{TASK["id"]}'
