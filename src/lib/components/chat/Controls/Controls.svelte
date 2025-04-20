<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	const dispatch = createEventDispatcher();
	const i18n = getContext<{ t: (key: string) => string }>('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user } from '$lib/stores';
	
	interface ChatFile {
		name: string;
		type: string;
		size?: number;
		url?: string;
	}

	interface ChatParams {
		system: string;
		stream_response: null;
		function_calling: null;
		seed: null;
		stop: null;
		temperature: null;
		reasoning_effort: null;
		logit_bias: null;
		frequency_penalty: null;
		repeat_last_n: null;
		mirostat: null;
		mirostat_eta: null;
		mirostat_tau: null;
		top_k: null;
		top_p: null;
		min_p: null;
		tfs_z: null;
		num_ctx: null;
		num_batch: null;
		num_keep: null;
		max_tokens: null;
		use_mmap: null;
		use_mlock: null;
		num_thread: null;
		num_gpu: null;
		template: null;
	}

	export let models: any[] = [];
	export let chatFiles: ChatFile[] = [];
	export let params: Partial<ChatParams> = {};

	// Initialize params with default values if not set
	$: {
		if (params && Object.keys(params).length === 0) {
			params = { ...DEFAULT_PARAMS };
		}
	}

	let showValves = false;

	// Define default parameters to compare against
	const DEFAULT_PARAMS = {
		system: '',
		stream_response: null,
		function_calling: null,
		seed: null,
		stop: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		frequency_penalty: null,
		repeat_last_n: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		top_k: null,
		top_p: null,
		min_p: null,
		tfs_z: null,
		num_ctx: null,
		num_batch: null,
		num_keep: null,
		max_tokens: null,
		use_mmap: null,
		use_mlock: null,
		num_thread: null,
		num_gpu: null,
		template: null
	};

	// Reactive variable to track if any control differs from default
	export let controlsActive = false; // Export the variable

	$: {
		controlsActive = false; // Reset before checking
		if (params) {
			// Check system prompt
			if (params.system !== DEFAULT_PARAMS.system) {
				controlsActive = true;
			}

			// Check advanced params (excluding system)
			for (const key in DEFAULT_PARAMS) {
				if (key !== 'system' && params.hasOwnProperty(key) && params[key] !== DEFAULT_PARAMS[key]) {
					controlsActive = true;
					break; // Exit loop early if any difference is found
				}
			}
		}
	}
</script>

<div
	class="bg-white dark:bg-gray-850 rounded-lg shadow-sm border border-gray-100 dark:border-gray-800 flex flex-col max-w-[380px]"
>
	<!-- Header -->
	<div
		class="flex items-center justify-between px-2.5 py-2 border-b border-gray-100 dark:border-gray-700/50"
	>
		<div class="flex items-center">
			<h2 class="text-base font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Chat Controls')}
			</h2>
			{#if controlsActive}
				<span
					class="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 text-xs font-small rounded-full inline-flex items-center gap-1 transition-all duration-200"
				>
					<span class="inline-block text-xs">✓</span>
					<span>{$i18n.t('Changes Active')}</span>
				</span>
			{/if}
		</div>

		<button
			class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full p-1 transition-colors duration-200"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>

	<!-- Content -->
	<div class="p-2 space-y-2.5 overflow-y-auto flex-1">
		{#if chatFiles.length > 0}
			<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 px-2 transition-colors duration-150">
				<div class="flex flex-col gap-1 pt-1.5" slot="content">
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

			<hr class="my-3 border-gray-100 dark:border-gray-700/50" />
		{/if}

		<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full text-sm rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 px-2 transition-colors duration-150">
			<div class="text-sm pt-1.5" slot="content">
				<Valves show={showValves} />
			</div>
		</Collapsible>

		{#if $user?.role === 'admin' || $user?.permissions.chat?.controls}
			<hr class="my-3 border-gray-100 dark:border-gray-700/50" />

			<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full text-sm rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 px-2 transition-colors duration-150">
				<div class="pt-1.5" slot="content">
					<textarea
						bind:value={params.system}
						class="w-full text-sm p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-blue-500 dark:focus:border-blue-400 outline-none resize-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 hover:border-gray-300 dark:hover:border-gray-600"
						rows="3"
						placeholder={$i18n.t('Enter system prompt')}
					/>
				</div>
			</Collapsible>

			<hr class="my-3 border-gray-100 dark:border-gray-700/50" />

			<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full text-sm rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 px-2 transition-colors duration-150">
				<div class="text-sm pt-1.5" slot="content">
					<div>
						<AdvancedParams admin={$user?.role === 'admin'} bind:params />
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
</div>
