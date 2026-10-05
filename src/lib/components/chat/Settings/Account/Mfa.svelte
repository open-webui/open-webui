<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { mfaRequest, type MfaChallenge } from '$lib/apis/auths/mfa';
	import MfaChallengeForm from '$lib/components/auth/MfaChallenge.svelte';
	import MfaRecoveryCodes from '$lib/components/auth/MfaRecoveryCodes.svelte';
	const i18n: any = getContext('i18n');
	let status: { enabled: boolean; required: boolean; recovery_codes_remaining: number } | null =
		null;
	let challenge: MfaChallenge | null = null;
	let codes: string[] = [];
	let code = '';
	let recovery = false;
	let busy = false;
	let error = '';
	let reauthenticate = false;
	let show = false;
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-700 disabled:opacity-40 dark:text-gray-500 dark:hover:text-gray-200';
	onMount(async () => {
		try {
			status = await mfaRequest('status', undefined, localStorage.token);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});
	const signIn = () => {
		localStorage.removeItem('token');
		window.location.href = '/auth?state=logout&form=signin';
	};
	const manage = async (replace: boolean) => {
		busy = true;
		error = '';
		try {
			const response = await mfaRequest(
				replace ? 'replace' : 'recovery/codes',
				{ code, recovery },
				localStorage.token
			);
			code = '';
			if (replace) challenge = response;
			else codes = response.recovery_codes;
		} catch (e) {
			reauthenticate = e instanceof Error && e.message === 'reauthentication_required';
			error = reauthenticate
				? $i18n.t('Sign in again before changing your authenticator settings.')
				: e instanceof Error
					? e.message
					: String(e);
		} finally {
			busy = false;
		}
	};
</script>

<div class="space-y-2.5 text-xs">
	{#if codes.length}
		<div class="w-full sm:max-w-md"><MfaRecoveryCodes {codes} onContinue={signIn} /></div>
	{:else if challenge}
		<div class="w-full sm:max-w-md">
			<MfaChallengeForm
				{challenge}
				onComplete={signIn}
				onCancel={() => {
					challenge = null;
				}}
			/>
		</div>
	{:else if status}
		<div class="flex items-center justify-between gap-2.5">
			<span class="text-gray-600 dark:text-gray-400"
				>{status.enabled
					? $i18n.t('Authenticator configured')
					: $i18n.t('Authenticator not configured')}</span
			>
			{#if status.required && status.enabled}<button
					type="button"
					class={actionButtonClass}
					on:click={() => {
						show = !show;
					}}>{show ? $i18n.t('Hide') : $i18n.t('Manage')}</button
				>{/if}
		</div>
		<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
			{status.enabled
				? $i18n.t('{{COUNT}} recovery codes remaining', { COUNT: status.recovery_codes_remaining })
				: $i18n.t('Managed by your administrator.')}
		</p>
		{#if show && status.required && status.enabled}
			<div class="w-full sm:max-w-md space-y-2.5 py-1">
				<p class="text-[0.6875rem] leading-4 text-gray-400 dark:text-gray-500">
					{$i18n.t('Verify with a fresh code. Changes sign out all devices.')}
				</p>
				<label class="block text-gray-600 dark:text-gray-400"
					>{recovery ? $i18n.t('Recovery code') : $i18n.t('Authenticator code')}<input
						class="mt-1 h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
						autocomplete="one-time-code"
						bind:value={code}
						maxlength={recovery ? 128 : 6}
						inputmode={recovery ? 'text' : 'numeric'}
					/></label
				>
				<label class="flex items-center gap-2 text-[0.6875rem] text-gray-500"
					><input
						class="size-3 rounded-sm"
						type="checkbox"
						bind:checked={recovery}
						on:change={() => {
							code = '';
						}}
					/>{$i18n.t('Use a recovery code')}</label
				>
				<div class="flex flex-wrap gap-4">
					<button
						type="button"
						class={actionButtonClass}
						disabled={busy || !code}
						on:click={() => manage(true)}>{$i18n.t('Replace authenticator')}</button
					><button
						type="button"
						class={actionButtonClass}
						disabled={busy || !code}
						on:click={() => manage(false)}>{$i18n.t('Generate recovery codes')}</button
					>
				</div>
			</div>
		{/if}
	{/if}
	{#if error}<p role="alert" class="text-[0.6875rem] text-red-500">{error}</p>{/if}
	{#if reauthenticate}<button type="button" class={actionButtonClass} on:click={signIn}
			>{$i18n.t('Sign in again')}</button
		>{/if}
</div>
