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

	let showValves = false;
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
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
	<div class="flex-1 overflow-y-auto py-4 space-y-4 text-sm">
		<!-- Files Section -->
		{#if chatFiles.length > 0}
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
					<div class="flex flex-col gap-2 mt-3" slot="content">
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
		<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
			<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
				<div class="mt-3" slot="content">
					<Valves show={showValves} />
				</div>
			</Collapsible>
		</div>

		<!-- Admin/Permission Sections -->
		{#if $user?.role === 'admin' || $user?.permissions.chat?.controls}
			<!-- System Prompt Section -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
					<div class="mt-3" slot="content">
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
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
					<div class="mt-3" slot="content">
						<AdvancedParams admin={$user?.role === 'admin'} bind:params />
					</div>
				</Collapsible>
			</div>
		{/if}
	</div>
</div>