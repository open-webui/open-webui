<script>
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	export let models = [];

	export let chatFiles = [];
	export let params = {};
</script>

<div class=" dark:text-white">
	<div class=" flex justify-between dark:text-gray-100 mb-2">
		<div class=" text-lg font-medium self-center font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			class="self-center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-4" />
		</button>
	</div>

	<div class=" dark:text-gray-200 text-sm font-primary py-0.5">
		{#if chatFiles.length > 0}
			<Collapsible title={$i18n.t('Files')} open={true}>
				<div class="flex flex-col gap-1 mt-1.5" slot="content">
					{#each chatFiles as file, fileIdx}
						<FileItem
							className="w-full"
							url={`${file?.url}`}
							name={file.name}
							type={file.type}
							size={file?.size}
							dismissible={true}
							on:dismiss={() => {
								// Remove the file from the chatFiles array

								chatFiles.splice(fileIdx, 1);
								chatFiles = chatFiles;
							}}
						/>
					{/each}
				</div>
			</Collapsible>

			<hr class="my-2 border-gray-100 dark:border-gray-800" />
		{/if}

		<Collapsible title={$i18n.t('Valves')}>
			<div class="text-sm mt-1.5" slot="content">
				<Valves />
			</div>
		</Collapsible>

		<hr class="my-2 border-gray-100 dark:border-gray-800" />

		<Collapsible title={$i18n.t('System Prompt')} open={true}>
			<div class=" mt-1.5" slot="content">
				<textarea
					bind:value={params.system}
					class="w-full rounded-lg px-3.5 py-2.5 text-sm dark:text-gray-300 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 outline-none resize-none"
					rows="4"
					placeholder={$i18n.t('Enter system prompt')}
				/>
			</div>
		</Collapsible>

		<hr class="my-2 border-gray-100 dark:border-gray-800" />

		<Collapsible title={$i18n.t('Advanced Params')} open={true}>
			<div class="text-sm mt-1.5" slot="content">
				<div>
					<AdvancedParams bind:params />
				</div>
			</div>
		</Collapsible>
	</div>
</div>
