<script context="module" lang="ts">
	import type { MfaChallenge } from '$lib/apis/auths/mfa';
	export type MfaManagementFlow =
		| { challenge: MfaChallenge }
		| { code: string; recovery: boolean; token: string };
</script>

<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { mfaRequest } from '$lib/apis/auths/mfa';
	import { user } from '$lib/stores';
	import MfaChallengeForm from './MfaChallenge.svelte';
	import MfaRecoveryCodes from './MfaRecoveryCodes.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');
	export let flow: MfaManagementFlow;
	export let onClose: () => void;
	let codes: string[] = [];
	let error = '';
	let reauthenticate = false;

	const signIn = async () => {
		localStorage.removeItem('token');
		user.set(undefined);
		await goto('/auth?state=logout&form=signin', { replaceState: true });
		onClose();
	};

	const cancel = async () => {
		if (!$user) await signIn();
		else onClose();
	};

	onMount(async () => {
		if ('challenge' in flow) return;
		try {
			const response = await mfaRequest(
				'recovery/codes',
				{ code: flow.code, recovery: flow.recovery },
				flow.token
			);
			codes = response.recovery_codes;
		} catch (e) {
			reauthenticate = e instanceof Error && e.message === 'reauthentication_required';
			error = reauthenticate
				? $i18n.t('Sign in again before changing your authenticator settings.')
				: e instanceof Error
					? e.message
					: String(e);
		}
	});
</script>

<main id="main-content" class="flex min-h-screen items-center justify-center px-5 py-10">
	<div class="w-full max-w-sm">
		{#if 'challenge' in flow}
			<MfaChallengeForm challenge={flow.challenge} onComplete={signIn} onCancel={cancel} />
		{:else if codes.length}
			<MfaRecoveryCodes {codes} onContinue={signIn} />
		{:else if error}
			<p role="alert" class="text-xs text-red-500">{error}</p>
			<button
				type="button"
				class="mt-3 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200"
				on:click={reauthenticate ? signIn : cancel}
			>
				{reauthenticate || !$user ? $i18n.t('Sign in again') : $i18n.t('Back')}
			</button>
		{:else}
			<div role="status" class="flex items-center justify-center gap-2 text-xs text-gray-500">
				<Spinner />
				{$i18n.t('Loading...')}
			</div>
		{/if}
	</div>
</main>
