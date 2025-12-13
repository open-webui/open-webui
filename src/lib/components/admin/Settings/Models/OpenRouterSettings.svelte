<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import {
		getOpenRouterConfig,
		updateOpenRouterConfig,
		type OpenRouterConfig
	} from '$lib/apis/openrouter';

	const i18n = getContext('i18n');

	let loading = true;
	let saving = false;

	let config: OpenRouterConfig | null = null;
	let anonymousEnabled = false;

	let apiKeyInput = '';
	let showApiKey = false;

	const load = async () => {
		loading = true;
		try {
			config = await getOpenRouterConfig(localStorage.token);
			anonymousEnabled = config.OPENROUTER_ANONYMOUS_ENABLED;
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	};

	const updateAnonymous = async () => {
		if (saving) return;
		saving = true;
		try {
			config = await updateOpenRouterConfig(localStorage.token, {
				OPENROUTER_ANONYMOUS_ENABLED: anonymousEnabled
			});
			anonymousEnabled = config.OPENROUTER_ANONYMOUS_ENABLED;
			toast.success($i18n.t('OpenRouter settings updated'));
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	};

	const updateKey = async () => {
		const key = apiKeyInput.trim();
		if (!key || saving) return;

		saving = true;
		try {
			config = await updateOpenRouterConfig(localStorage.token, {
				OPENROUTER_API_KEY: key
			});
			apiKeyInput = '';
			toast.success($i18n.t('OpenRouter API key updated'));
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	};

	const clearKey = async () => {
		if (!config?.OPENROUTER_API_KEY_SET || saving) return;

		saving = true;
		try {
			config = await updateOpenRouterConfig(localStorage.token, {
				OPENROUTER_API_KEY: ''
			});
			apiKeyInput = '';
			toast.success($i18n.t('OpenRouter API key cleared'));
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	};

	onMount(load);
</script>

<div class="mb-4">
	<div class="flex items-center justify-between px-0.5">
		<div class="text-base font-medium">OpenRouter</div>
		<div class="flex items-center gap-2">
			<button
				class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-100 transition"
				type="button"
				disabled={loading || saving}
				on:click={load}
			>
				{$i18n.t('Refresh')}
			</button>
		</div>
	</div>

	<div class="mt-2 rounded-lg border border-gray-100/30 dark:border-gray-850/30 p-3">
		{#if loading}
			<div class="flex items-center gap-2 text-sm text-gray-500">
				<Spinner className="size-4" />
				{$i18n.t('Loading')}
			</div>
		{:else if config}
			<div class="flex flex-col gap-3">
				<div class="text-xs text-gray-500 dark:text-gray-400">
					<div>
						{$i18n.t('Default model')}: <span class="font-mono">{config.OPENROUTER_DEFAULT_MODEL_ID}</span>
					</div>
					<div>
						{$i18n.t('Base URL')}: <span class="font-mono">{config.OPENROUTER_API_BASE_URL}</span>
					</div>
				</div>

				<div class="flex items-center justify-between gap-3">
					<div class="text-sm font-medium">{$i18n.t('Enable for anonymous users')}</div>
					<div class="flex items-center gap-2 {saving ? 'pointer-events-none opacity-50' : ''}">
						<Switch
							bind:state={anonymousEnabled}
							on:change={() => {
								updateAnonymous();
							}}
						/>
					</div>
				</div>

				{#if anonymousEnabled && !config.OPENROUTER_API_KEY_SET}
					<div class="text-xs text-amber-600 dark:text-amber-400">
						{$i18n.t('Anonymous access requires an OpenRouter API key.')}
					</div>
				{/if}

				<div class="flex flex-col gap-1.5">
					<div class="flex items-center justify-between">
						<div class="text-sm font-medium">{$i18n.t('OpenRouter API Key')}</div>
						{#if config.OPENROUTER_API_KEY_SET}
							<div class="text-xs text-green-700 dark:text-green-400">
								{$i18n.t('Key is set')}
							</div>
						{:else}
							<div class="text-xs text-amber-700 dark:text-amber-400">
								{$i18n.t('Key is not set')}
							</div>
						{/if}
					</div>

					<div class="flex items-center gap-2">
						<input
							class="flex-1 text-sm px-3 py-2 rounded-lg bg-transparent border border-gray-100/30 dark:border-gray-850/30 outline-hidden"
							type={showApiKey ? 'text' : 'password'}
							bind:value={apiKeyInput}
							placeholder={config.OPENROUTER_API_KEY_SET
								? $i18n.t('Enter a new key to replace the current one')
								: $i18n.t('Enter OpenRouter API key')}
						/>

						<Tooltip content={showApiKey ? $i18n.t('Hide') : $i18n.t('Show')}>
							<button
								class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								type="button"
								on:click={() => {
									showApiKey = !showApiKey;
								}}
							>
								{#if showApiKey}
									<EyeSlash className="size-4" />
								{:else}
									<Eye className="size-4" />
								{/if}
							</button>
						</Tooltip>
					</div>

					<div class="flex items-center gap-2">
						<button
							class="text-sm px-3 py-1.5 rounded-lg bg-gray-900 text-white dark:bg-white dark:text-black disabled:opacity-50"
							type="button"
							disabled={saving || apiKeyInput.trim() === ''}
							on:click={updateKey}
						>
							{$i18n.t('Update key')}
						</button>

						<button
							class="text-sm px-3 py-1.5 rounded-lg border border-gray-100/30 dark:border-gray-850/30 disabled:opacity-50"
							type="button"
							disabled={saving || !config.OPENROUTER_API_KEY_SET}
							on:click={clearKey}
						>
							{$i18n.t('Clear key')}
						</button>
					</div>
				</div>
			</div>
		{:else}
			<div class="text-sm text-gray-500">{$i18n.t('Failed to load')}</div>
		{/if}
	</div>
</div>
