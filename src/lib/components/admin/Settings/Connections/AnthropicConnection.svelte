<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import {
		getAnthropicAuthUrl,
		getAnthropicAuthStatus,
		exchangeAnthropicCode,
		anthropicLogout,
		type AnthropicAuthStatus
	} from '$lib/apis/anthropic';

	const i18n = getContext('i18n');

	export let onStatusChange: (authenticated: boolean) => void = () => {};

	let status: AnthropicAuthStatus = { authenticated: false };
	let loading = true;
	let connecting = false;
	let authCode = '';
	let authState = '';
	let exchanging = false;

	const checkAuthStatus = async () => {
		try {
			status = await getAnthropicAuthStatus(localStorage.token);
			onStatusChange(status.authenticated);
		} catch (err) {
			console.error('Failed to check Anthropic auth status:', err);
			status = { authenticated: false };
		}
	};

	const startOAuthFlow = async () => {
		connecting = true;
		try {
			const { url, state } = await getAnthropicAuthUrl(localStorage.token);
			authState = state;
			window.open(url, '_blank', 'noopener');
		} catch (err) {
			console.error('Failed to start OAuth flow:', err);
			toast.error($i18n.t('Failed to start authentication'));
		} finally {
			connecting = false;
		}
	};

	const submitAuthCode = async () => {
		const raw = authCode.trim();
		if (!raw) {
			toast.error($i18n.t('Please paste the authorization code'));
			return;
		}

		if (!authState) {
			toast.error($i18n.t('Click "Connect with Claude" first to start the auth flow'));
			return;
		}

		const parts = raw.split('#');
		const code = parts[0];
		if (!code) {
			toast.error($i18n.t('Invalid code format'));
			return;
		}

		exchanging = true;
		try {
			await exchangeAnthropicCode(localStorage.token, code, authState);
			authCode = '';
			authState = '';
			await checkAuthStatus();
			if (status.authenticated) {
				toast.success($i18n.t('Connected to Claude successfully'));
			}
		} catch (err: any) {
			console.error('Failed to exchange code:', err);
			toast.error(typeof err === 'string' ? err : $i18n.t('Failed to exchange authorization code'));
		} finally {
			exchanging = false;
		}
	};

	const disconnect = async () => {
		try {
			await anthropicLogout(localStorage.token);
			status = { authenticated: false };
			onStatusChange(false);
			toast.success($i18n.t('Disconnected from Claude'));
		} catch (err) {
			console.error('Failed to disconnect:', err);
			toast.error($i18n.t('Failed to disconnect'));
		}
	};

	onMount(async () => {
		await checkAuthStatus();
		loading = false;
	});
</script>

<div class="flex flex-col w-full gap-2">
	{#if loading}
		<div class="flex items-center gap-2 text-gray-500">
			<Spinner className="size-4" />
			<span class="text-sm">{$i18n.t('Checking connection...')}</span>
		</div>
	{:else if status.authenticated}
		<div class="flex w-full items-center justify-between">
			<div class="flex items-center gap-2">
				<div class="flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/30">
					<svg class="w-5 h-5 text-amber-600 dark:text-amber-400" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
					</svg>
				</div>
				<div class="flex flex-col">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{status.display_name || status.email || $i18n.t('Connected')}
					</span>
					{#if status.email && status.display_name}
						<span class="text-xs text-gray-500 dark:text-gray-400">{status.email}</span>
					{/if}
				</div>
			</div>

			<Tooltip content={$i18n.t('Disconnect')}>
				<button
					class="px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
					on:click={disconnect}
					type="button"
				>
					{$i18n.t('Disconnect')}
				</button>
			</Tooltip>
		</div>
	{:else}
		<div class="flex flex-col gap-3">
			<div class="flex w-full items-center justify-between">
				<span class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Not connected')}
				</span>
				<button
					class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-600 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={startOAuthFlow}
					disabled={connecting}
					type="button"
				>
					{#if connecting}
						<Spinner className="size-4" />
						<span>{$i18n.t('Connecting...')}</span>
					{:else}
						<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
						</svg>
						<span>{$i18n.t('Connect with Claude')}</span>
					{/if}
				</button>
			</div>

			<div class="flex gap-2">
				<input
					type="text"
					bind:value={authCode}
					placeholder={$i18n.t('Paste authorization code here...')}
					class="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none"
					on:keydown={(e) => {
						if (e.key === 'Enter') submitAuthCode();
					}}
					disabled={exchanging}
				/>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-600 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={submitAuthCode}
					disabled={exchanging || !authCode.trim()}
					type="button"
				>
					{#if exchanging}
						<Spinner className="size-4" />
					{:else}
						{$i18n.t('Submit')}
					{/if}
				</button>
			</div>
		</div>
	{/if}
</div>
