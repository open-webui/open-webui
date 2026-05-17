<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import {
		disableTOTP,
		enableTOTP,
		getTOTPStatus,
		regenerateTOTPBackupCodes,
		setupTOTP
	} from '$lib/apis/auths';
	import { copyToClipboard } from '$lib/utils';

	const i18n: Writable<i18nType> = getContext('i18n');

	type TOTPStatus = {
		enabled: boolean;
		created_at?: number | null;
		last_used_at?: number | null;
		backup_codes_remaining: number;
		backup_codes?: string[];
	};

	type TOTPSetup = {
		secret: string;
		otpauth_url: string;
	};

	let loaded = false;
	let status: TOTPStatus | null = null;
	let setup: TOTPSetup | null = null;
	let setupCode = '';
	let backupCodes: string[] = [];

	let action: 'disable' | 'regenerate' | '' = '';
	let actionCode = '';
	let actionBackupCode = '';
	let useBackupCode = false;

	const loadStatus = async () => {
		status = await getTOTPStatus(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		loaded = true;
	};

	const startSetupHandler = async () => {
		setup = await setupTOTP(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		setupCode = '';
	};

	const enableHandler = async () => {
		const res = await enableTOTP(localStorage.token, setupCode).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			status = res;
			setup = null;
			setupCode = '';
			backupCodes = res.backup_codes ?? [];
			toast.success($i18n.t('Two-factor authentication enabled.'));
		}
	};

	const resetAction = () => {
		action = '';
		actionCode = '';
		actionBackupCode = '';
		useBackupCode = false;
	};

	const disableHandler = async () => {
		const res = await disableTOTP(
			localStorage.token,
			useBackupCode ? null : actionCode,
			useBackupCode ? actionBackupCode : null
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			status = res;
			backupCodes = [];
			resetAction();
			toast.success($i18n.t('Two-factor authentication disabled.'));
		}
	};

	const regenerateBackupCodesHandler = async () => {
		const res = await regenerateTOTPBackupCodes(
			localStorage.token,
			useBackupCode ? null : actionCode,
			useBackupCode ? actionBackupCode : null
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			status = res;
			backupCodes = res.backup_codes ?? [];
			resetAction();
			toast.success($i18n.t('Backup codes regenerated.'));
		}
	};

	const submitActionHandler = async () => {
		if (action === 'disable') {
			await disableHandler();
		} else if (action === 'regenerate') {
			await regenerateBackupCodesHandler();
		}
	};

	const copyBackupCodesHandler = () => {
		copyToClipboard(backupCodes.join('\n'));
		toast.success($i18n.t('Copied to clipboard'));
	};

	onMount(async () => {
		await loadStatus();
	});
</script>

{#if loaded && status}
	<div class="mt-2">
		<div class="flex justify-between items-center text-sm">
			<div class="font-medium">{$i18n.t('Two-factor authentication')}</div>

			{#if status.enabled}
				<div class="text-xs text-emerald-600 dark:text-emerald-400">{$i18n.t('Enabled')}</div>
			{:else if !setup}
				<button
					class="text-xs font-medium text-gray-500"
					type="button"
					on:click={startSetupHandler}>{$i18n.t('Enable')}</button
				>
			{/if}
		</div>

		{#if setup}
			<div class="mt-3 space-y-2">
				<a class="text-xs underline" href={setup.otpauth_url}>{$i18n.t('Open authenticator app')}</a>

				<div>
					<div class="mb-1 text-xs font-medium">{$i18n.t('Setup key')}</div>
					<div class="flex">
						<input
							class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
							type="text"
							value={setup.secret}
							readonly
							aria-label={$i18n.t('Setup key')}
						/>
						<button
							class="ml-1.5 px-1.5 py-1 dark:hover:bg-gray-850 transition rounded-lg text-xs"
							type="button"
							on:click={() => {
								if (!setup) {
									return;
								}
								copyToClipboard(setup.secret);
								toast.success($i18n.t('Copied to clipboard'));
							}}
						>
							{$i18n.t('Copy')}
						</button>
					</div>
				</div>

				<div>
					<label for="totp-setup-code" class="mb-1 text-xs font-medium block"
						>{$i18n.t('Authenticator code')}</label
					>
					<input
						id="totp-setup-code"
						class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
						type="text"
						inputmode="numeric"
						autocomplete="one-time-code"
						bind:value={setupCode}
						placeholder={$i18n.t('Enter 6-digit code')}
					/>
				</div>

				<div class="flex justify-end gap-2">
					<button
						class="px-3 py-1.5 text-xs font-medium rounded-full bg-gray-100/70 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition"
						type="button"
						on:click={() => {
							setup = null;
							setupCode = '';
						}}
					>
						{$i18n.t('Cancel')}
					</button>

					<button
						class="px-3 py-1.5 text-xs font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="button"
						on:click={enableHandler}
					>
						{$i18n.t('Verify')}
					</button>
				</div>
			</div>
		{:else if backupCodes.length > 0}
			<div class="mt-3 space-y-2">
				<div class="text-xs font-medium">{$i18n.t('Backup codes')}</div>
				<div class="grid grid-cols-2 gap-1 text-xs font-mono">
					{#each backupCodes as code}
						<div class="py-1">{code}</div>
					{/each}
				</div>

				<div class="flex justify-end gap-2">
					<button
						class="px-3 py-1.5 text-xs font-medium rounded-full bg-gray-100/70 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition"
						type="button"
						on:click={copyBackupCodesHandler}
					>
						{$i18n.t('Copy')}
					</button>

					<button
						class="px-3 py-1.5 text-xs font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="button"
						on:click={() => {
							backupCodes = [];
							loadStatus();
						}}
					>
						{$i18n.t('Done')}
					</button>
				</div>
			</div>
		{:else if status.enabled}
			<div class="mt-2 space-y-2">
				<div class="text-xs text-gray-500">
					{$i18n.t('Backup codes remaining')}: {status.backup_codes_remaining}
				</div>

				<div class="flex gap-2">
					<button
						class="text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							action = action === 'regenerate' ? '' : 'regenerate';
						}}
					>
						{$i18n.t('New backup codes')}
					</button>

					<button
						class="text-xs font-medium text-red-500"
						type="button"
						on:click={() => {
							action = action === 'disable' ? '' : 'disable';
						}}
					>
						{$i18n.t('Disable')}
					</button>
				</div>

				{#if action}
					<div class="space-y-2">
						{#if useBackupCode}
							<div>
								<label for="totp-action-backup" class="mb-1 text-xs font-medium block"
									>{$i18n.t('Backup code')}</label
								>
								<input
									id="totp-action-backup"
									class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									autocomplete="one-time-code"
									bind:value={actionBackupCode}
									placeholder={$i18n.t('Enter backup code')}
								/>
							</div>
						{:else}
							<div>
								<label for="totp-action-code" class="mb-1 text-xs font-medium block"
									>{$i18n.t('Authenticator code')}</label
								>
								<input
									id="totp-action-code"
									class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									inputmode="numeric"
									autocomplete="one-time-code"
									bind:value={actionCode}
									placeholder={$i18n.t('Enter 6-digit code')}
								/>
							</div>
						{/if}

						<div class="flex justify-between items-center">
							<button
								class="text-xs underline"
								type="button"
								on:click={() => {
									useBackupCode = !useBackupCode;
									actionCode = '';
									actionBackupCode = '';
								}}
							>
								{useBackupCode
									? $i18n.t('Use authenticator code')
									: $i18n.t('Use backup code')}
							</button>

							<button
								class="px-3 py-1.5 text-xs font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								type="button"
								on:click={submitActionHandler}
							>
								{action === 'disable' ? $i18n.t('Disable') : $i18n.t('Regenerate')}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
