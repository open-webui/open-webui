<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import { models } from '$lib/stores';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Image from '$lib/components/common/Image.svelte';

	export let show = false;
	export let selectedModelId = '';
	export let files = [];

	export let onUpdate = (files: any[]) => {
		// Default no-op function
	};
</script>

<div class="flex items-center mb-1.5 pt-1.5">
	<div class=" -translate-x-1.5 flex items-center">
		<button
			class="p-0.5 bg-transparent transition rounded-lg"
			on:click={() => {
				show = !show;
			}}
		>
			<XMark className="size-5" strokeWidth="2.5" />
		</button>
	</div>

	<div class=" font-medium text-base flex items-center gap-1">
		<div>
			{$i18n.t('Controls')}
		</div>
	</div>
</div>

<div class="mt-1">
	<div class="pb-10">
		{#if files.length > 0}
			<div class=" text-xs font-medium pb-1">{$i18n.t('Files')}</div>

			<div class="flex flex-col gap-1">
				{#each files.filter((file) => file.type !== 'image') as file, fileIdx}
					<FileItem
						className="w-full"
						item={file}
						small={true}
						edit={true}
						dismissible={true}
						url={file.url}
						name={file.name}
						type={file.type}
						size={file?.size}
						loading={file.status === 'uploading'}
						on:dismiss={() => {
							// Remove the file from the files array
							files = files.filter((item) => item.id !== file.id);
							files = files;

							onUpdate(files);
						}}
						on:click={() => {
							console.log(file);
						}}
					/>
				{/each}

				<div class="flex items-center flex-wrap gap-2 mt-1.5">
					{#each files.filter((file) => file.type === 'image') as file, fileIdx}
						<Image
							src={file.url}
							imageClassName=" size-14 rounded-xl object-cover"
							dismissible={true}
							onDismiss={() => {
								files = files.filter((item) => item.id !== file.id);
								files = files;

								onUpdate(files);
							}}
						/>
					{/each}
				</div>
			</div>

			<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
		{/if}

		<div class=" text-xs font-medium mb-1">{$i18n.t('Model')}</div>

		<div class="w-full">
			<select class="w-full bg-transparent text-sm outline-hidden" bind:value={selectedModelId}>
				<option value="" class="bg-gray-50 dark:bg-gray-700" disabled>
					{$i18n.t('Select a model')}
				</option>
				{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
					<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
				{/each}
			</select>
		</div>
	</div>
</div>
