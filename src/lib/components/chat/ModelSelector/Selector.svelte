<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { marked } from 'marked';
	import Fuse from 'fuse.js';

	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import { deleteModel, getOllamaVersion, pullModel } from '$lib/apis/ollama';

	import {
		user,
		MODEL_DOWNLOAD_POOL,
		models,
		mobile,
		temporaryChatEnabled,
		settings,
		config
	} from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { capitalizeFirstLetter, sanitizeResponseContent, splitStream } from '$lib/utils';
	import { getModels } from '$lib/apis';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';
	export let value = '';
	export let placeholder = 'Select a model';
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search a model');
	export let showTemporaryChatControl = false;

	export let items: {
		label: string;
		value: string;
		model: Model;
		[key: string]: any;
	}[] = [];

	export let className = 'w-[32rem]';
	export let triggerClassName = 'text-lg';

	let show = false;
	let tags = [];
	let selectedModel = '';
	$: selectedModel = items.find((item) => item.value === value) ?? '';

	let searchValue = '';
	let selectedTag = '';
	let selectedConnectionType = '';
	let ollamaVersion = null;
	let selectedModelIdx = 0;

	const fuse = new Fuse(
		items.map((item) => ({
			...item,
			modelName: item.model?.name,
			tags: (item.model?.tags ?? []).map((tag) => tag.name).join(' '),
			desc: item.model?.info?.meta?.description
		})),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.4
		}
	);

	$: filteredItems = (
		searchValue
			? fuse.search(searchValue).map((e) => e.item)
			: items
	)
		.filter((item) => {
			if (selectedTag && !(item.model?.tags ?? []).map((tag) => tag.name).includes(selectedTag)) {
				return false;
			}
			if (selectedConnectionType === 'ollama') {
				return item.model?.owned_by === 'ollama';
			} else if (selectedConnectionType === 'openai') {
				return item.model?.owned_by === 'openai';
			} else if (selectedConnectionType === 'direct') {
				return item.model?.direct;
			}
			return true;
		})
		.filter((item) => !(item.model?.info?.meta?.hidden ?? false));

	$: if (selectedTag || selectedConnectionType) {
		resetView();
	}

	const resetView = async () => {
		await tick();
		const selectedInFiltered = filteredItems.findIndex((item) => item.value === value);
		selectedModelIdx = selectedInFiltered >= 0 ? selectedInFiltered : 0;
		await tick();
		// document.querySelector(`[data-arrow-selected="true"]`)?.scrollIntoView({ 
		// 	block: 'center', 
		// 	inline: 'nearest', 
		// 	behavior: 'instant' 
		// });
	};

	const pullModelHandler = async () => {
		const sanitizedModelTag = searchValue.trim().replace(/^ollama\s+(run|pull)\s+/, '');

		if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: sanitizedModelTag
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length === 3) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		const [res, controller] = await pullModel(localStorage.token, sanitizedModelTag, '0').catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL,
				[sanitizedModelTag]: {
					...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
					abortController: controller,
					reader,
					done: false
				}
			});

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							if (data.error) throw data.error;
							if (data.detail) throw data.detail;

							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.completed) {
										downloadProgress = Math.round((data.completed / data.total) * 1000) / 10;
									} else {
										downloadProgress = 100;
									}

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											pullProgress: downloadProgress,
											digest: data.digest
										}
									});
								} else {
									toast.success(data.status);

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											done: data.status === 'success'
										}
									});
								}
							}
						}
					}
				} catch (error) {
					toast.error(`${typeof error === 'string' ? error : error.message}`);
					break;
				}
			}

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag].done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];
			MODEL_DOWNLOAD_POOL.set({ ...$MODEL_DOWNLOAD_POOL });
		}
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch(() => false);

		if (items) {
			tags = items
				.filter((item) => !(item.model?.info?.meta?.hidden ?? false))
				.flatMap((item) => item.model?.tags ?? [])
				.map((tag) => tag.name);

			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}
	});

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) abortController.abort();
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({ ...$MODEL_DOWNLOAD_POOL });
			await deleteModel(localStorage.token, model);
			toast.success(`${model} download has been canceled`);
		}
	};
</script>

<DropdownMenu.Root
	bind:open={show}
	
	trapFocus={false}  
	onOpenChange={async () => {
		searchValue = '';
		requestAnimationFrame(() => {
	document.getElementById('model-search-input')?.focus({ preventScroll: true });
});

		resetView();
	}}
	closeFocus={false}
>
	<DropdownMenu.Trigger
	type="button"
	class="relative w-full font-primary"
	aria-label={placeholder}
	id="model-selector-{id}-button"
>
		<div
			class="flex w-full items-center justify-between px-0.5 outline-none bg-transparent {triggerClassName} font-medium text-gray-700 dark:text-gray-100 hover:text-gray-900 dark:hover:text-white transition-colors"
		>
			<span class="truncate">
				{selectedModel ? selectedModel.label : placeholder}
			</span>
			<ChevronDown className="ml-2 size-3.5 shrink-0 opacity-60" strokeWidth="2.5" />
		</div>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class="z-40 {$mobile ? 'w-full' : className} max-w-[calc(100vw-1rem)] rounded-xl bg-white dark:bg-gray-850 shadow-xl border border-gray-200 dark:border-gray-700/50 outline-none overflow-hidden"
		transition={flyAndScale}
		side={$mobile ? 'bottom' : 'bottom-start'}
		sideOffset={4}
	>
		<slot>
			{#if searchEnabled}
				<div class="px-4 pt-3 pb-2 border-b border-gray-100 dark:border-gray-800">
					<div class="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 focus-within:bg-gray-100 dark:focus-within:bg-gray-800 transition-colors">
						<Search className="size-4 text-gray-400" strokeWidth="2.5" />
						<input
							id="model-search-input"
							bind:value={searchValue}
							class="w-full text-sm bg-transparent outline-none text-gray-700 dark:text-gray-100 placeholder-gray-400"
							placeholder={searchPlaceholder}
							autocomplete="off"
							on:keydown={(e) => {
								if (e.code === 'Enter' && filteredItems.length > 0) {
									value = filteredItems[selectedModelIdx].value;
									show = false;
									return;
								} else if (e.code === 'ArrowDown') {
									selectedModelIdx = Math.min(selectedModelIdx + 1, filteredItems.length - 1);
								} else if (e.code === 'ArrowUp') {
									selectedModelIdx = Math.max(selectedModelIdx - 1, 0);
								} else {
									selectedModelIdx = 0;
								}

								// document.querySelector(`[data-arrow-selected="true"]`)?.scrollIntoView({ 
								// 	block: 'center', 
								// 	inline: 'nearest', 
								// 	behavior: 'instant' 
								// });
							}}
						/>
					</div>
				</div>
			{/if}

			<!-- Filter Tabs -->
			{#if tags.length > 0 || items.some(item => item.model?.owned_by === 'ollama' || item.model?.owned_by === 'openai' || item.model?.direct)}
				<div class="px-4 py-2 border-b border-gray-100 dark:border-gray-800 overflow-x-auto scrollbar-thin">
					<div class="flex gap-1.5 w-fit">
						<button
							class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap {selectedTag === '' && selectedConnectionType === ''
								? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
								: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
							on:click={() => {
								selectedConnectionType = '';
								selectedTag = '';
							}}
						>
							{$i18n.t('All')}
						</button>

						{#if items.find((item) => item.model?.owned_by === 'ollama') && items.find((item) => item.model?.owned_by === 'openai')}
							<button
								class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap {selectedConnectionType === 'ollama'
									? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
									: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => {
									selectedTag = '';
									selectedConnectionType = 'ollama';
								}}
							>
								{$i18n.t('Local')}
							</button>
							<button
								class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap {selectedConnectionType === 'openai'
									? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
									: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => {
									selectedTag = '';
									selectedConnectionType = 'openai';
								}}
							>
								{$i18n.t('External')}
							</button>
						{/if}

						{#if items.find((item) => item.model?.direct)}
							<button
								class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap {selectedConnectionType === 'direct'
									? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
									: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => {
									selectedTag = '';
									selectedConnectionType = 'direct';
								}}
							>
								{$i18n.t('Direct')}
							</button>
						{/if}

						{#each tags as tag}
							<button
								class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap capitalize {selectedTag === tag
									? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
									: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => {
									selectedConnectionType = '';
									selectedTag = tag;
								}}
							>
								{tag}
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Model List -->
			<div class="max-h-[400px] overflow-y-auto scrollbar-thin py-2">
				{#each filteredItems as item, index}
					<button
						aria-label="model-item"
						class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors {index === selectedModelIdx ? 'bg-gray-50 dark:bg-gray-800/50' : ''}"
						data-arrow-selected={index === selectedModelIdx}
						data-value={item.value}
						on:click={() => {
							value = item.value;
							selectedModelIdx = index;
							show = false;
						}}
					>
						<!-- Model Icon -->
						<img
							src={item.model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
							alt="Model"
							class="rounded-full size-8 shrink-0"
						/>

						<!-- Model Info -->
						<div class="flex-1 min-w-0 text-left">
							<div class="flex items-center gap-2">
								<span class="font-medium truncate">{item.label}</span>
								
								<!-- Connection Type Icon -->
								{#if item.model?.direct}
									<Tooltip content="Direct">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5 text-gray-400">
											<path fill-rule="evenodd" d="M2 2.75A.75.75 0 0 1 2.75 2C8.963 2 14 7.037 14 13.25a.75.75 0 0 1-1.5 0c0-5.385-4.365-9.75-9.75-9.75A.75.75 0 0 1 2 2.75Zm0 4.5a.75.75 0 0 1 .75-.75 6.75 6.75 0 0 1 6.75 6.75.75.75 0 0 1-1.5 0C8 10.35 5.65 8 2.75 8A.75.75 0 0 1 2 7.25ZM3.5 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" clip-rule="evenodd" />
										</svg>
									</Tooltip>
								{:else if item.model?.owned_by === 'openai'}
									<Tooltip content="External">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5 text-gray-400">
											<path fill-rule="evenodd" d="M8.914 6.025a.75.75 0 0 1 1.06 0 3.5 3.5 0 0 1 0 4.95l-2 2a3.5 3.5 0 0 1-5.396-4.402.75.75 0 0 1 1.251.827 2 2 0 0 0 3.085 2.514l2-2a2 2 0 0 0 0-2.828.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
											<path fill-rule="evenodd" d="M7.086 9.975a.75.75 0 0 1-1.06 0 3.5 3.5 0 0 1 0-4.95l2-2a3.5 3.5 0 0 1 5.396 4.402.75.75 0 0 1-1.251-.827 2 2 0 0 0-3.085-2.514l-2 2a2 2 0 0 0 0 2.828.75.75 0 0 1 0 1.06Z" clip-rule="evenodd" />
										</svg>
									</Tooltip>
								{/if}

								<!-- Info Icon -->
								{#if item.model?.info?.meta?.description}
									<Tooltip content={marked.parse(sanitizeResponseContent(item.model?.info?.meta?.description).replaceAll('\n', '<br>'))}>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-3.5 text-gray-400">
											<path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
										</svg>
									</Tooltip>
								{/if}
							</div>

							<!-- Parameter Size & Tags -->
							<div class="flex items-center gap-1.5 mt-0.5">
								{#if item.model?.owned_by === 'ollama' && item.model.ollama?.details?.parameter_size}
									<span class="text-xs text-gray-500 dark:text-gray-400">
										{item.model.ollama.details.parameter_size}
									</span>
								{/if}
								
								{#if item.model?.tags?.length > 0}
									<div class="flex gap-1">
										{#each item.model.tags.slice(0, 2) as tag}
											<span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
												{tag.name}
											</span>
										{/each}
									</div>
								{/if}
							</div>
						</div>

						<!-- Check Icon -->
						{#if value === item.value}
							<div class="shrink-0 text-gray-900 dark:text-white">
								<Check />
							</div>
						{/if}
					</button>
				{:else}
					<div class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('No results found')}
					</div>
				{/each}

				<!-- Pull Model Option -->
				{#if !(searchValue.trim() in $MODEL_DOWNLOAD_POOL) && searchValue && ollamaVersion && $user?.role === 'admin'}
					<button
						class="flex w-full items-center px-4 py-2.5 text-sm text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border-t border-gray-100 dark:border-gray-800"
						on:click={pullModelHandler}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4 mr-2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
						</svg>
						{$i18n.t(`Pull "{{searchValue}}" from Ollama.com`, { searchValue: searchValue })}
					</button>
				{/if}

				<!-- Download Progress -->
				{#each Object.keys($MODEL_DOWNLOAD_POOL) as model}
					<div class="flex items-center justify-between px-4 py-2.5 text-sm border-t border-gray-100 dark:border-gray-800">
						<div class="flex items-center gap-2 flex-1 min-w-0">
							<svg class="size-4 animate-spin text-gray-600" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
								<path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/>
								<path d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"/>
							</svg>
							<div class="flex-1 min-w-0">
								<div class="text-gray-700 dark:text-gray-100 truncate">
									Downloading "{model}"
									{'pullProgress' in $MODEL_DOWNLOAD_POOL[model] ? `(${$MODEL_DOWNLOAD_POOL[model].pullProgress}%)` : ''}
								</div>
								{#if 'digest' in $MODEL_DOWNLOAD_POOL[model] && $MODEL_DOWNLOAD_POOL[model].digest}
									<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
										{$MODEL_DOWNLOAD_POOL[model].digest}
									</div>
								{/if}
							</div>
						</div>
						<button
							class="shrink-0 ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
							on:click={() => cancelModelPullHandler(model)}
						>
							<svg class="size-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
				{/each}
			</div>

			<!-- Temporary Chat Control -->
			{#if showTemporaryChatControl}
				<div class="px-4 py-3 border-t border-gray-100 dark:border-gray-800">
					<button
						class="flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
						on:click={async () => {
							temporaryChatEnabled.set(!$temporaryChatEnabled);
							await goto('/');
							setTimeout(() => document.getElementById('new-chat-button')?.click(), 0);

							if ($temporaryChatEnabled) {
								history.replaceState(null, '', '?temporary-chat=true');
							} else {
								history.replaceState(null, '', location.pathname);
							}
							show = false;
						}}
					>
						<div class="flex items-center gap-2.5">
							<ChatBubbleOval className="size-4" strokeWidth="2.5" />
							<span class="font-medium">{$i18n.t('Temporary Chat')}</span>
						</div>
						<Switch state={$temporaryChatEnabled} />
					</button>
				</div>
			{/if}
		</slot>
	</DropdownMenu.Content>
</DropdownMenu.Root>

<style>
	.scrollbar-thin::-webkit-scrollbar {
		width: 6px;
		height: 6px;
	}
	
	.scrollbar-thin::-webkit-scrollbar-track {
		background: transparent;
	}
	
	.scrollbar-thin::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.3);
		border-radius: 3px;
	}
	
	.scrollbar-thin::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.5);
	}
</style>