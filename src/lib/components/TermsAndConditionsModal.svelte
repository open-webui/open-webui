<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Modal from './common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let show = false;
	export let termsUrl = 'https://www.luxtronic.ai/terms';

	let agreed = false;

	const handleClose = () => {
		if (!agreed) return;
		dispatch('agree');
		show = false;
	};
</script>

<Modal bind:show size="xl" dismissable={agreed}>
	<div class="px-6 pt-5 dark:text-white text-black">
		<div class="flex justify-between items-start">
			<div class="text-xl font-medium">
				{$i18n.t('Terms and Conditions')}
			</div>
			<button
				class="self-center disabled:opacity-40 disabled:cursor-not-allowed"
				disabled={!agreed}
				on:click={handleClose}
				aria-label={$i18n.t('Close')}
			>
				<XMark className={'size-5'}>
					<p class="sr-only">{$i18n.t('Close')}</p>
				</XMark>
			</button>
		</div>
		<div class="text-sm dark:text-gray-200 mt-1">
			{$i18n.t('Please review and accept the terms to continue.')}
		</div>
	</div>

	<div class="w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class="rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800 bg-white/50 dark:bg-gray-900/40">
			<iframe
				title={$i18n.t('Terms and Conditions')}
				src={termsUrl}
				class="w-full h-[55vh]"
			/>
		</div>

		<div class="mt-4 flex items-center gap-2">
			<input
				id="terms-agree-checkbox"
				type="checkbox"
				class="size-4 accent-blue-600"
				bind:checked={agreed}
			/>
			<label for="terms-agree-checkbox" class="text-sm">
				{$i18n.t('I agree to the Terms and Conditions')}
			</label>
		</div>

		<div class="flex justify-end pt-4 text-sm font-medium">
			<button
				on:click={handleClose}
				disabled={!agreed}
				class="px-3.5 py-1.5 text-sm font-medium rounded-full transition disabled:opacity-40 disabled:cursor-not-allowed bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
			>
				<span class="relative">{$i18n.t('Continue')}</span>
			</button>
		</div>
	</div>
</Modal>
