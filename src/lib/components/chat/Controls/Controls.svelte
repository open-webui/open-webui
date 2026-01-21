<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params = {};

	let showValves = false;
</script>

<div class="dark:text-white">
	<div class="flex items-center justify-between mb-3 pb-2 border-b border-gray-100 dark:border-gray-800">
		<div class="text-base font-semibold text-gray-900 dark:text-white font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-4" strokeWidth="2" />
		</button>
	</div>

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class="dark:text-gray-200 text-sm font-primary space-y-3">
			{#if chatFiles.length > 0}
				<div class="bg-gray-50/50 dark:bg-gray-800/30 rounded-xl p-3">
					<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
						<div class="flex flex-col gap-1.5 mt-2" slot="content">
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
									small={true}
									on:dismiss={() => {
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

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true)}
				<div class="bg-gray-50/50 dark:bg-gray-800/30 rounded-xl p-3">
					<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
						<div class="text-sm mt-2" slot="content">
							<Valves show={showValves} />
						</div>
					</Collapsible>
				</div>
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<div class="bg-gray-50/50 dark:bg-gray-800/30 rounded-xl p-3">
					<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
						<div class="mt-2" slot="content">
							<textarea
								bind:value={params.system}
								class="w-full text-xs outline-hidden resize-vertical rounded-lg {$settings.highContrastMode
									? 'border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2.5'
									: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-2.5'}"
								rows="4"
								placeholder={$i18n.t('Enter system prompt')}
							/>
						</div>
					</Collapsible>
				</div>
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<div class="bg-gray-50/50 dark:bg-gray-800/30 rounded-xl p-3">
					<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
						<div class="text-sm mt-2" slot="content">
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
						</div>
					</Collapsible>
				</div>
			{/if}
		</div>
	{/if}
</div>
