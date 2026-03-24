<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params = {};

	const sectionClass =
		'rounded-xl border border-gray-200/90 dark:border-gray-700 bg-white dark:bg-gray-800/80 shadow-sm';
	const sectionButtonClass =
		'w-full px-3 py-2.5 rounded-xl text-sm font-semibold text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';

	let showFiles = true;
	let showValves = false;
	let showSystemPrompt = false;
	let showAdvancedParams = false;
</script>

<div class="flex flex-col h-full min-h-0">
	<!-- Header -->
	<div class="sticky top-0 z-10 flex items-center justify-between bg-gray-50 dark:bg-gray-900 px-1 py-2 border-b border-gray-200 dark:border-gray-700">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Chat Controls')}
		</h2>
		<button
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
			on:click={() => {
				dispatch('close');
			}}
			aria-label="Close"
		>
			<XMark className="size-4" />
		</button>
	</div>

	<!-- Content -->
	<div class="flex-1 min-h-0 overflow-y-auto py-2.5 space-y-2.5 text-sm pr-0.5">
		<!-- Files Section -->
		{#if chatFiles.length > 0}
			<div class={sectionClass}>
				<Collapsible bind:open={showFiles} title={$i18n.t('Files')} buttonClassName={sectionButtonClass}>
					<div class="px-3 pb-3 pt-0.5 flex flex-col gap-2" slot="content">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								on:dismiss={() => {
									// Remove the file from the chatFiles array
									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</Collapsible>
			</div>
		{/if}

		<!-- Valves Section -->
		<div class={sectionClass}>
			<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName={sectionButtonClass}>
				<div class="px-3 pb-3 pt-0.5" slot="content">
					<Valves show={showValves} />
				</div>
			</Collapsible>
		</div>

		<!-- Admin/Permission Sections -->
		{#if $user?.role === 'admin' || $user?.permissions.chat?.controls}
			<!-- System Prompt Section -->
			<div class={sectionClass}>
				<Collapsible
					bind:open={showSystemPrompt}
					title={$i18n.t('System Prompt')}
					buttonClassName={sectionButtonClass}
				>
					<div class="px-3 pb-3 pt-0.5" slot="content">
						<textarea
							bind:value={params.system}
							class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none resize-none placeholder:text-gray-400 dark:placeholder:text-gray-500 transition-colors"
							rows="4"
							placeholder={$i18n.t('Enter system prompt')}
						/>
					</div>
				</Collapsible> 
			</div>

			<!-- Advanced Params Section -->
			<div class={sectionClass}>
				<Collapsible
					bind:open={showAdvancedParams}
					title={$i18n.t('Advanced Params')}
					buttonClassName={sectionButtonClass}
				>
					<div class="px-3 pb-3 pt-0.5" slot="content">
						<AdvancedParams admin={$user?.role === 'admin'} bind:params />
					</div>
				</Collapsible>
			</div>
		{/if}
	</div>
</div>