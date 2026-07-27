<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { getContext } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { acknowledgeUserDisclaimer } from '$lib/apis/auths';

	const i18n = getContext('i18n');

	export let show = false;

	let acknowledging = false;

	const acknowledge = async () => {
		if (acknowledging) {
			return;
		}
		acknowledging = true;

		const res = await acknowledgeUserDisclaimer(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
		acknowledging = false;

		if (res === null) {
			// Keep the disclaimer up: an acknowledgement we failed to record is no acknowledgement.
			toast.error($i18n.t('Failed to save the acknowledgement. Please try again.'));
			return;
		}

		await settings.set({
			...$settings,
			userDisclaimerVersion: res.user_disclaimer_version ?? '',
			userDisclaimerAcknowledgedAt: res.user_disclaimer_acknowledged_at ?? null
		});
		show = false;
	};
</script>

<div class="fixed w-full h-full flex z-999">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div
					class="text-center dark:text-white text-2xl font-medium z-50"
					style="white-space: pre-wrap;"
				>
					{#if ($config?.ui?.user_disclaimer_title ?? '').trim() !== ''}
						{$config.ui.user_disclaimer_title}
					{:else}
						{$i18n.t('Disclaimer')}
					{/if}
				</div>

				<div
					class=" mt-4 text-center text-sm dark:text-gray-200 w-full"
					style="white-space: pre-wrap;"
				>
					{@html DOMPurify.sanitize(
						marked.parse(($config?.ui?.user_disclaimer_content ?? '').replace(/\n/g, '<br>'))
					)}
				</div>

				<div class=" mt-6 mx-auto relative group w-fit">
					<button
						class="relative z-20 flex px-5 py-2 rounded-full bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition font-medium text-sm disabled:opacity-50"
						disabled={acknowledging}
						on:click={acknowledge}
					>
						{$i18n.t('I Acknowledge')}
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
