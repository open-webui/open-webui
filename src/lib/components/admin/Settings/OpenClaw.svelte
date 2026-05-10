<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getBackendConfig, getModels as _getModels } from '$lib/apis';
	import { getOpenClawConfig, setOpenClawConfig } from '$lib/apis/configs';
	import { config, models, settings } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	let loading = true;
	let saving = false;

	let openClawConfig = {
		ENABLE_OPENCLAW_GATEWAY: false,
		OPENCLAW_GATEWAY_URL: 'ws://127.0.0.1:18789',
		OPENCLAW_GATEWAY_TOKEN: '',
		OPENCLAW_GATEWAY_CLIENT_ID: 'gateway-client',
		OPENCLAW_GATEWAY_CLIENT_MODE: 'backend',
		OPENCLAW_GATEWAY_DEVICE_PATH: '',
		OPENCLAW_ALLOWED_AGENT_IDS: []
	};

	let allowedAgentIdsText = '';

	const refreshModels = async () => {
		await models.set(
			await _getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
				false,
				true
			)
		);
	};

	const saveHandler = async () => {
		saving = true;
		const payload = {
			...openClawConfig,
			OPENCLAW_ALLOWED_AGENT_IDS: allowedAgentIdsText
				.split(',')
				.map((agentId) => agentId.trim())
				.filter(Boolean)
		};

		const res = await setOpenClawConfig(localStorage.token, payload).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			openClawConfig = res;
			allowedAgentIdsText = (res.OPENCLAW_ALLOWED_AGENT_IDS ?? []).join(', ');
			await config.set(await getBackendConfig());
			await refreshModels();
			dispatch('save');
		}
		saving = false;
	};

	onMount(async () => {
		const res = await getOpenClawConfig(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			openClawConfig = res;
			allowedAgentIdsText = (res.OPENCLAW_ALLOWED_AGENT_IDS ?? []).join(', ');
		}
		loading = false;
	});
</script>

{#if !loading}
	<div class="flex flex-col gap-5 text-sm">
		<div class="flex items-center justify-between gap-4">
			<div>
				<div class="font-medium text-gray-900 dark:text-gray-100">OpenClaw Gateway</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Expose OpenClaw Agents as selectable chat agents.')}
				</div>
			</div>
			<Switch bind:state={openClawConfig.ENABLE_OPENCLAW_GATEWAY} />
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-gateway-url">
				{$i18n.t('Gateway URL')}
			</label>
			<input
				id="openclaw-gateway-url"
				class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
				bind:value={openClawConfig.OPENCLAW_GATEWAY_URL}
				placeholder="ws://127.0.0.1:18789"
			/>
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-gateway-token">
				{$i18n.t('Gateway Token')}
			</label>
			<input
				id="openclaw-gateway-token"
				type="password"
				class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
				bind:value={openClawConfig.OPENCLAW_GATEWAY_TOKEN}
				autocomplete="off"
			/>
		</div>

		<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
			<div class="flex flex-col gap-1">
				<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-client-id">
					{$i18n.t('Client ID')}
				</label>
				<input
					id="openclaw-client-id"
					class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
					bind:value={openClawConfig.OPENCLAW_GATEWAY_CLIENT_ID}
				/>
			</div>
			<div class="flex flex-col gap-1">
				<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-client-mode">
					{$i18n.t('Client Mode')}
				</label>
				<input
					id="openclaw-client-mode"
					class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
					bind:value={openClawConfig.OPENCLAW_GATEWAY_CLIENT_MODE}
				/>
			</div>
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-device-path">
				{$i18n.t('Device Identity Path')}
			</label>
			<input
				id="openclaw-device-path"
				class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
				bind:value={openClawConfig.OPENCLAW_GATEWAY_DEVICE_PATH}
				placeholder="Default: DATA_DIR/openclaw_gateway_device.json"
			/>
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-xs font-medium text-gray-700 dark:text-gray-300" for="openclaw-agent-allowlist">
				{$i18n.t('Allowed Agent IDs')}
			</label>
			<input
				id="openclaw-agent-allowlist"
				class="w-full rounded-lg border border-gray-200 bg-transparent px-3 py-2 outline-hidden dark:border-gray-700"
				bind:value={allowedAgentIdsText}
				placeholder="main, sales, support"
			/>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Leave empty to expose all agents returned by OpenClaw.')}
			</div>
		</div>

		<div>
			<button
				class="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
				disabled={saving}
				on:click={saveHandler}
			>
				{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
			</button>
		</div>
	</div>
{/if}
