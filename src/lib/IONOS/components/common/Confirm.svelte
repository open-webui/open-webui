<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	export let title = '';
	export let message = '';
	export let show = false;
	export let confirmText = $i18n.t('OK');
	export let confirmHandler = () => { };
	export let cancelText = $i18n.t('Cancel');
	export let cancelHandler = () => { };

	let confirmed = false;
</script>

<Dialog
	closable={false}
	{title}
	dialogId="confirmation-dialog"
	{show}
>
	<div class="flex flex-col min-w-[400px] max-w-[400px]">
		<div class="">
			{message}
		</div>

		<div class="flex flex-row justify-end pt-8 pb-2">
			<button
				class="shrink px-4 0 hover:bg-sky-100 active:bg-sky-50 rounded-3xl"
				on:click={cancelHandler}
			>
				{cancelText}
			</button>

			<button
				class="shrink px-4 py-1 text-red-700 hover:text-white hover:bg-red-300/90 active:bg-red-300 rounded-3xl"
				disabled={confirmed}
				on:click={() => { confirmed = true; confirmHandler() }}
			>
				{confirmText}
			</button>
		</div>
	</div>
</Dialog>
