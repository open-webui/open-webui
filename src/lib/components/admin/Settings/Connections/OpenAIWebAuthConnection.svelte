<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		completeOpenAIWebAuth,
		disconnectOpenAIWebAuth,
		getOpenAIWebAuthStatus,
		startOpenAIWebAuth,
		type OpenAIWebAuthStart,
		type OpenAIWebAuthStatus
	} from '$lib/apis/openai';

	const i18n = getContext('i18n');

	export let configured = false;
	export let onUseCredential: () => Promise<void> | void = () => {};

	let status: OpenAIWebAuthStatus | null = null;
	let pendingAuthorization: OpenAIWebAuthStart | null = null;
	let loading: 'status' | 'start' | 'complete' | 'disconnect' | 'configure' | null = null;
	let error = '';

	const formatExpiration = (expiresAt?: number | null) => {
		if (!expiresAt) {
			return '';
		}
		return new Date(expiresAt * 1000).toLocaleString();
	};

	const refreshStatus = async () => {
		loading = 'status';
		error = '';
		const res = await getOpenAIWebAuthStatus(localStorage.token).catch((err) => {
			error = `${err}`;
		});
		if (res) {
			status = res;
		}
		loading = null;
	};

	const startHandler = async () => {
		loading = 'start';
		error = '';
		const res = await startOpenAIWebAuth(localStorage.token).catch((err) => {
			error = `${err}`;
			toast.error(`${err}`);
		});

		if (res) {
			pendingAuthorization = res;
			status = {
				credential_type: status?.credential_type ?? 'none',
				connected: false,
				has_credential: status?.has_credential ?? false,
				status: 'awaiting_authorization',
				expires_at: res.expires_at
			};
			toast.success($i18n.t('OpenAI authorization started'));
		}

		loading = null;
	};

	const completeHandler = async () => {
		if (!pendingAuthorization?.session_id) {
			return;
		}

		loading = 'complete';
		error = '';
		const res = await completeOpenAIWebAuth(
			localStorage.token,
			pendingAuthorization.session_id
		).catch((err) => {
			error = `${err}`;
			toast.error(`${err}`);
		});

		if (res) {
			status = res;
			pendingAuthorization = null;
			if (res.connected) {
				await Promise.resolve(onUseCredential()).catch((err) => {
					error = `${err}`;
					toast.error(`${err}`);
				});
				toast.success($i18n.t('OpenAI account auth connected'));
			} else {
				toast.error($i18n.t('OpenAI account auth requires reconnect'));
			}
		}

		loading = null;
	};

	const disconnectHandler = async () => {
		loading = 'disconnect';
		error = '';
		const res = await disconnectOpenAIWebAuth(localStorage.token).catch((err) => {
			error = `${err}`;
			toast.error(`${err}`);
		});

		if (res) {
			status = res;
			pendingAuthorization = null;
			toast.success($i18n.t('OpenAI account auth disconnected'));
		}

		loading = null;
	};

	const useCredentialHandler = async () => {
		loading = 'configure';
		error = '';
		await Promise.resolve(onUseCredential()).catch((err) => {
			error = `${err}`;
			toast.error(`${err}`);
		});
		loading = null;
	};

	onMount(() => {
		refreshStatus();
	});
</script>

<div class="mt-3 rounded-xl border border-gray-100 dark:border-gray-850 p-3 space-y-2">
	<div class="flex items-start justify-between gap-3">
		<div>
			<div class="font-medium text-xs">{$i18n.t('OpenAI Account Auth')}</div>
			<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t(
					'Connect OpenAI with an account authorization flow. API-key connections remain available above.'
				)}
			</div>
		</div>

		{#if loading === 'status'}
			<Spinner />
		{/if}
	</div>

	{#if status}
		<div class="text-xs text-gray-600 dark:text-gray-300">
			{#if status.connected}
				{$i18n.t('Status')}: {$i18n.t('Connected')}
			{:else if status.status === 'reconnect_required'}
				{$i18n.t('Status')}: {$i18n.t('Reconnect required')}
			{:else if pendingAuthorization}
				{$i18n.t('Status')}: {$i18n.t('Awaiting authorization')}
			{:else}
				{$i18n.t('Status')}: {$i18n.t('Not connected')}
			{/if}
		</div>

		{#if status.expires_at}
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Expires')}: {formatExpiration(status.expires_at)}
			</div>
		{/if}

		{#if status.connected}
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{#if configured}
					{$i18n.t('This account auth is enabled for account-auth compatible OpenAI models.')}
				{:else}
					{$i18n.t('Enable it for account-auth compatible OpenAI models before use.')}
				{/if}
			</div>
		{/if}
	{/if}

	{#if pendingAuthorization}
		<div class="rounded-lg bg-gray-50 dark:bg-gray-850 p-2 space-y-1.5 text-xs">
			<div class="flex justify-between gap-2">
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('User code')}</span>
				<span class="font-mono tracking-wide">{pendingAuthorization.user_code}</span>
			</div>

			<div class="flex justify-between gap-2">
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Authorization page')}</span>
				<a
					class="underline font-medium"
					href={pendingAuthorization.verification_url}
					target="_blank"
					rel="noreferrer"
				>
					{$i18n.t('Open OpenAI authorization page')}
				</a>
			</div>

			<div class="flex justify-between gap-2">
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Check interval')}</span>
				<span>{$i18n.t('{{seconds}} seconds', { seconds: pendingAuthorization.interval })}</span>
			</div>

			<div class="flex justify-between gap-2">
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Code expires')}</span>
				<span>{formatExpiration(pendingAuthorization.expires_at)}</span>
			</div>
		</div>
	{/if}

	{#if error}
		<div class="text-xs text-red-500">{error}</div>
	{/if}

	<div class="flex flex-wrap gap-2 pt-1">
		{#if pendingAuthorization}
			<button
				class="px-3 py-1 text-xs font-medium rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
				type="button"
				disabled={loading !== null}
				on:click={completeHandler}
			>
				{$i18n.t('I’ve authorized')}
				{#if loading === 'complete'}<Spinner />{/if}
			</button>
		{:else if status?.connected}
			{#if !configured}
				<button
					class="px-3 py-1 text-xs font-medium rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
					type="button"
					disabled={loading !== null}
					on:click={useCredentialHandler}
				>
					{$i18n.t('Use for account-auth models')}
					{#if loading === 'configure'}<Spinner />{/if}
				</button>
			{/if}

			<button
				class="px-3 py-1 text-xs font-medium rounded-full border border-gray-200 dark:border-gray-800 disabled:opacity-50"
				type="button"
				disabled={loading !== null}
				on:click={startHandler}
			>
				{$i18n.t('Reconnect')}
				{#if loading === 'start'}<Spinner />{/if}
			</button>
		{:else}
			<button
				class="px-3 py-1 text-xs font-medium rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
				type="button"
				disabled={loading !== null}
				on:click={startHandler}
			>
				{$i18n.t('Connect with OpenAI')}
				{#if loading === 'start'}<Spinner />{/if}
			</button>
		{/if}

		{#if status?.has_credential || pendingAuthorization}
			<button
				class="px-3 py-1 text-xs font-medium rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
				type="button"
				disabled={loading !== null}
				on:click={disconnectHandler}
			>
				{$i18n.t('Disconnect')}
				{#if loading === 'disconnect'}<Spinner />{/if}
			</button>
		{/if}
	</div>
</div>
