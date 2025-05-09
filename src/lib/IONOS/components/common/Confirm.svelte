<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import DialogHeader from '$lib/IONOS/components/common/DialogHeader.svelte';

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
	dialogId="confirmation-dialog"
	{show}
>
	<DialogHeader
			slot="header"
			{title}
			closable={false}
			dialogId="confirmation-dialog"
			class="mb-2.5"
		/>
	<div slot="content" class="flex flex-col min-w-[calc(400px-60px)] max-w-[calc(550px-60px)] text-blue-800">
		<div class="mb-2.5 text-sm" >
			{message}
		</div>

		<div class="flex flex-row justify-end mt-2.5">
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
