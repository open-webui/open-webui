<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	export let title = '';
	export let message = '';
	export let show = false;
	export let confirmText = $i18n.t('OK');
	export let confirmHandler = () => { };
	export let cancelText = $i18n.t('Cancel');
	export let cancelHandler = () => { };
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
			<Button
				on:click={cancelHandler}
				type={ButtonType.tertiary}
			>
				{cancelText}
			</Button>

			<Button
				on:click={() => { confirmHandler() }}
				type={ButtonType.caution}
			>
				{confirmText}
			</Button>
		</div>
	</div>
</Dialog>
