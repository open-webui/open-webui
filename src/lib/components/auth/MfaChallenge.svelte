<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { mfaRequest, type MfaChallenge } from '$lib/apis/auths/mfa';
	import MfaRecoveryCodes from './MfaRecoveryCodes.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	const i18n: any = getContext('i18n');
	export let challenge: MfaChallenge;
	export let onComplete: (result: any) => void | Promise<void>;
	export let onCancel: () => void;
	let setup: { manual_key: string; qr_code: string } | null = null;
	let code = '';
	let recovery = false;
	let busy = false;
	let error = '';
	let result: any = null;

	const loadSetup = async () => {
		if (challenge.next_step !== 'enroll') return;
		busy = true;
		try {
			setup = await mfaRequest('enroll/start', { challenge_token: challenge.challenge_token });
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	};
	onMount(loadSetup);

	const verify = async () => {
		if (busy || !code.trim()) return;
		busy = true;
		error = '';
		try {
			if (challenge.next_step === 'recover') {
				challenge = await mfaRequest('recover', {
					challenge_token: challenge.challenge_token,
					reset_token: code.trim()
				});
				code = '';
				await loadSetup();
			} else {
				const response = await mfaRequest(
					challenge.next_step === 'enroll' ? 'enroll/confirm' : 'verify',
					{
						challenge_token: challenge.challenge_token,
						code: code.trim(),
						recovery
					}
				);
				code = '';
				setup = null;
				if (response.recovery_codes) result = response;
				else await onComplete(response);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	};
</script>

<div class="space-y-3 text-left text-xs text-gray-700 dark:text-gray-300">
	{#if result}
		<MfaRecoveryCodes
			codes={result.recovery_codes}
			onContinue={() => {
				const { recovery_codes, ...completed } = result;
				result = null;
				onComplete(completed);
			}}
		/>
	{:else}
		<div>
			<h2 class="text-base font-medium tracking-tight text-gray-900 dark:text-white">
				{$i18n.t(
					challenge.next_step === 'enroll'
						? 'Set up your authenticator'
						: challenge.next_step === 'recover'
							? 'Recover your authenticator'
							: 'Verify your sign-in'
				)}
			</h2>
			<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
				{$i18n.t(
					challenge.next_step === 'enroll'
						? 'Scan the QR code, then enter the six-digit code from your authenticator app.'
						: challenge.next_step === 'recover'
							? 'Enter the recovery token from your operator.'
							: recovery
								? 'Enter one of your saved recovery codes.'
								: 'Enter the six-digit code from your authenticator app.'
				)}
			</p>
		</div>
		{#if challenge.next_step === 'enroll'}
			{#if setup}
				<img
					class="mx-auto size-40 bg-white p-1"
					src={setup.qr_code}
					alt={$i18n.t('Authenticator setup QR code')}
				/>
				<details class="group text-[0.6875rem] text-gray-500 dark:text-gray-400">
					<summary
						class="flex cursor-pointer list-none items-center gap-1 hover:text-gray-900 dark:hover:text-white [&::-webkit-details-marker]:hidden"
					>
						{$i18n.t('Enter the key manually')}
						<ChevronRight className="size-2.5 shrink-0 transition-transform group-open:rotate-90" />
					</summary>
					<code
						class="mt-2 block break-all rounded-md bg-gray-50 px-2 py-1.5 font-mono text-gray-700 select-all dark:bg-white/[0.03] dark:text-gray-300"
						>{setup.manual_key}</code
					>
				</details>
			{:else if busy}<p role="status" class="py-2 text-gray-400">
					{$i18n.t('Preparing your authenticator…')}
				</p>
			{:else}<button
					type="button"
					class="text-gray-500 hover:text-gray-900 dark:hover:text-white"
					on:click={loadSetup}>{$i18n.t('Retry setup')}</button
				>{/if}
		{/if}
		<label class="block text-[0.8125rem] leading-5 font-normal text-left text-black dark:text-white">
			{$i18n.t(
				challenge.next_step === 'recover'
					? 'Operator recovery token'
					: recovery
						? 'Recovery code'
						: 'Authenticator code'
			)}
			<input
				class="my-0.5 w-full text-[0.8125rem] leading-5 outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
				bind:value={code}
				placeholder={$i18n.t(
					challenge.next_step === 'recover'
						? 'Enter your recovery token'
						: recovery
							? 'Enter your recovery code'
							: 'Enter your authenticator code'
				)}
				autocomplete="one-time-code"
				inputmode={recovery || challenge.next_step === 'recover' ? 'text' : 'numeric'}
				maxlength={challenge.next_step === 'recover' ? 160 : recovery ? 128 : 6}
				spellcheck="false"
				autocapitalize="none"
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						verify();
					}
				}}
			/>
		</label>
		{#if error}<p role="alert" class="text-xs leading-4 text-red-600 dark:text-red-400">
				{error}
			</p>{/if}
		<div class="flex justify-end text-black dark:text-white">
			<button
				type="button"
				class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-normal text-[0.8125rem] leading-5 py-2.5 disabled:opacity-50 flex justify-center"
				disabled={busy || !code.trim() || (challenge.next_step === 'enroll' && !setup)}
				on:click={verify}>{$i18n.t(busy ? 'Verifying…' : 'Continue')}</button
			>
		</div>
		<div
			class="flex flex-wrap items-center justify-between gap-2 text-[0.6875rem] text-gray-500 dark:text-gray-400"
		>
			<button
				type="button"
				class="transition-colors hover:text-gray-900 dark:hover:text-white"
				disabled={busy}
				on:click={onCancel}>{$i18n.t('Back to sign in')}</button
			>
			{#if challenge.next_step === 'verify'}<button
					type="button"
					class="transition-colors hover:text-gray-900 dark:hover:text-white"
					disabled={busy}
					on:click={() => {
						recovery = !recovery;
						code = '';
						error = '';
					}}>{$i18n.t(recovery ? 'Use an authenticator code' : 'Use a recovery code')}</button
				>{/if}
		</div>
	{/if}
</div>
