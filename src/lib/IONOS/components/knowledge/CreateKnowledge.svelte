<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME } from '$lib/stores';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'
	import { create as createKnowledge } from '$lib/IONOS/services/knowledge';
	import DialogHeader from '$lib/IONOS/components/common/DialogHeader.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	async function create() {
		if (name.trim() === '' || description.trim() === '') {
			console.error('The fields name and description may not be empty');
			return;
		}

		try {
			await createKnowledge(name, description);
			dispatch('created');
			toast.success($i18n.t('Knowledge created successfully.', { ns: 'ionos' }));
		} catch (e) {
			console.error('Can not create knowledge: ', e);
			toast.error($i18n.t('Error creating knowledge', { ns: 'ionos' }));
		}
	}

	let name = '';
	let description = '';
</script>

<svelte:head>
	<title>
		{$i18n.t('Create Knowledge', { ns: 'ionos' })} | {$WEBUI_NAME}
	</title>
</svelte:head>

<Dialog
	dialogId="knowledge-create"
	show={show}
	class="p-0"
>
	<DialogHeader
			slot="header"
			title={$i18n.t("Create a knowledge base", { ns: 'ionos' })}
			on:close={() => { dispatch('close'); }}
			dialogId="knowledge-create"
			class="p-[30px]"
		/>
	<form
		on:submit|preventDefault={create}
		class="flex flex-col gap-4 min-w-[500px] p-5"
		slot="content"
	>
		<div class="flex flex-col justify-center cursor-default gap-5">
			<h2 class="font-semibold text-sm text-blue-800 px-2.5">
				{$i18n.t('What are you working on?', { ns: 'ionos' })}
			</h2>

			<input
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 outline-none text-blue-800 placeholder:text-gray-400"
				bind:value={name}
				type="text"
				required
				placeholder={$i18n.t('Name your knowledge base', { ns: 'ionos' })}
			/>
		</div>

		<div class="flex flex-col justify-center cursor-default gap-5">
			<h2 class="font-semibold text-sm text-blue-800 px-2.5">
				{$i18n.t('What are you trying to achieve?', { ns: 'ionos' })}
			</h2>

			<textarea
				class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 text-blue-800 placeholder:text-gray-400 dark:text-gray-300 dark:bg-gray-850 outline-none"
				bind:value={description}
				rows="4"
				required
				placeholder={$i18n.t('Describe your knowledge base', { ns: 'ionos' })}
			/>
		</div>

		<div class="flex justify-end items-end py-4 cursor-default">
			<Button
				type={ButtonType.secondary}
			>
				{$i18n.t('Create knowledge base', { ns: 'ionos' })}
			</Button>
		</div>
	</form>
</Dialog>
