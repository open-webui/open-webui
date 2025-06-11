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

	import { user, MODEL_DOWNLOAD_POOL, models, mobile, temporaryChatEnabled } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { capitalizeFirstLetter, sanitizeResponseContent, splitStream } from '$lib/utils';
	import { getModels } from '$lib/apis';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import { goto } from '$app/navigation';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import StarRating from './IntelligenceRating.svelte';
	import SpeedRating from './SpeedRating.svelte';
	import { modelsInfo, mapModelsToOrganizations } from '../../../../data/modelsInfo';
	import { getModelIcon } from '$lib/utils';


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
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}[] = [];

	export let className = '180px';
	export let triggerClassName = 'text-xs';

	let show = false;

	let selectedModel = '';
	$: selectedModel = items.find((item) => item.value === value) ?? '';

	let searchValue = '';
	let ollamaVersion = null;

	let selectedModelIdx = 0;

	let modelGroups = mapModelsToOrganizations(modelsInfo);
	const desiredOrder = Object.values(modelGroups).flat();
	const orderMap = new Map(desiredOrder.map((name, index) => [name, index]));
	
	const filteredSourceItems = items
		.filter?.((item) => !item?.model?.name?.toLowerCase()?.includes('arena'))
		?.filter((item) => item.model?.base_model_id == null)
		.sort((a, b) => (orderMap.get(a?.model?.name) ?? Infinity) - (orderMap.get(b?.model?.name) ?? Infinity));
	console.log(filteredSourceItems, 'items');
	const fuse = new Fuse(
		filteredSourceItems.map((item) => {
			const _item = {
				...item,
				modelName: item.model?.name,
				tags: item.model?.meta?.tags?.map((tag) => tag.name).join(' '),
				desc: item.model?.meta?.description
			};
			return _item;
		}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.4
		}
	);

	$: filteredItems = searchValue
		? fuse.search(searchValue).map((e) => {
				return e.item;
			})
		: filteredSourceItems;

	const pullModelHandler = async () => {
		const sanitizedModelTag = searchValue.trim().replace(/^ollama\s+(run|pull)\s+/, '');

		console.log($MODEL_DOWNLOAD_POOL);
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
							console.log(data);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}

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
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}

					toast.error(`${error}`);
					// opts.callback({ success: false, error, modelName: opts.modelName });
					break;
				}
			}

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag].done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(await getModels(localStorage.token));
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
		}
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => false);
	});

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) {
			abortController.abort();
		}
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
			await deleteModel(localStorage.token, model);
			toast.success(`${model} download has been canceled`);
		}
	};

	let hoveredItem = null;

	let knowledgeCutoff = null;

	$: {
		if (modelsInfo?.[hoveredItem?.label]?.knowledge_cutoff) {
			const date = new Date(modelsInfo?.[hoveredItem?.label]?.knowledge_cutoff);

			const formatted = date.toLocaleString('default', {
				year: 'numeric',
				month: 'long'
			});
			knowledgeCutoff = formatted;
		}
	}
	let baseModel = null;
	$: {
		if (selectedModel?.model?.base_model_id) {
			baseModel = items.find((item) => item?.model?.id === selectedModel?.model?.base_model_id);
		}
	}
	
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={async () => {
		searchValue = '';
		selectedModelIdx = 0;
		window.setTimeout(() => document.getElementById('model-search-input')?.focus(), 0);
	}}
	closeFocus={false}
>
	{#if !selectedModel?.model?.base_model_id}
		<DropdownMenu.Trigger
			class="relative w-full flex"
			aria-label={placeholder}
			id="model-selector-{id}-button"
		>
			<div
				class="flex w-full text-left px-0.5 outline-none bg-transparent truncate {triggerClassName} justify-between dark:text-customGray-100 placeholder-gray-400 focus:outline-none"
			>
				{#if selectedModel}
					<img
						src={getModelIcon(selectedModel.label)}
						alt="Model"
						class="rounded-full size-4 self-center mr-2"
					/>
					{selectedModel.label}
				{:else}
					{placeholder}
				{/if}
				<ChevronDown className=" self-center ml-2 size-2" strokeWidth="2" />
			</div>
		</DropdownMenu.Trigger>
	{:else}
		<div
			class="flex w-full text-left px-0.5 outline-none bg-transparent truncate {triggerClassName} justify-between placeholder-gray-400 focus:outline-none"
		>
			{#if selectedModel}
				<img
					src={getModelIcon(baseModel?.model?.name)}
					alt="Model"
					class="rounded-full size-4 self-center mr-2"
				/>
				<!-- {selectedModel.label} -->
				{baseModel?.model?.name}
			{:else}
				{placeholder}
			{/if}
		</div>
	{/if}

	<DropdownMenu.Content
		class=" z-40 {$mobile
			? `w-full`
			: `${className}`} w-[180px] justify-start rounded-xl border dark:border-customGray-700 bg-lightGray-550 border-lightGray-400 dark:bg-customGray-900 dark:text-white shadow-lg  outline-none"
		transition={flyAndScale}
		side={$mobile ? 'bottom' : 'bottom-start'}
		sideOffset={5}
	>
		<slot>
			{#if searchEnabled}
				<div class="flex items-center relative gap-2.5 px-2.5 mt-2.5 mb-3">
					<div class="absolute left-5 text-customGray-300">
						<Search className="size-3" strokeWidth="2.5" />
					</div>

					<input
						id="model-search-input"
						bind:value={searchValue}
						class="w-full text-xs bg-transparent outline-none pl-7 h-[25px] rounded-lg border border-lightGray-400 dark:border-customGray-700 placeholder:text-xs"
						placeholder={searchPlaceholder}
						autocomplete="off"
						on:keydown={(e) => {
							if (e.code === 'Enter' && filteredItems.length > 0) {
								value = filteredItems[selectedModelIdx].value;
								show = false;
								return; // dont need to scroll on selection
							} else if (e.code === 'ArrowDown') {
								selectedModelIdx = Math.min(selectedModelIdx + 1, filteredItems.length - 1);
							} else if (e.code === 'ArrowUp') {
								selectedModelIdx = Math.max(selectedModelIdx - 1, 0);
							} else {
								// if the user types something, reset to the top selection.
								selectedModelIdx = 0;
							}

							const item = document.querySelector(`[data-arrow-selected="true"]`);
							item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
						}}
					/>
				</div>
			{/if}

			<div class="px-[3px] my-2 max-h-64 overflow-y-auto custom-scrollbar">
				{#each filteredItems as item, index}
					<button
						aria-label="model-item"
						class="flex w-full text-left line-clamp-1 select-none items-center rounded-button py-[5px] px-2 text-sm text-lightGray-100 dark:text-customGray-100 outline-none transition-all duration-75 hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:hover:text-white rounded-lg cursor-pointer {value ===
						item.value
							? 'bg-lightGray-700 dark:bg-customGray-950'
							: ''}"
						data-arrow-selected={index === selectedModelIdx}
						on:mouseenter={() => (hoveredItem = item)}
						on:mouseleave={() => (hoveredItem = null)}
						on:click={() => {
							value = item.value;
							selectedModelIdx = index;

							show = false;
						}}
					>
						<div class="flex flex-col">
							{#if $mobile && (item?.model?.meta?.tags ?? []).length > 0}
								<div class="flex gap-0.5 self-start h-full mb-1.5 -translate-x-1">
									{#each item.model?.meta.tags as tag}
										<div
											class=" text-xs font-bold px-1 rounded uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
										>
											{tag.name}
										</div>
									{/each}
								</div>
							{/if}
							<div class="flex items-center gap-2">
								<div class="flex items-center min-w-fit">
									<div class="line-clamp-1">
										<div class="flex items-center min-w-fit">
											<!-- <Tooltip
												content={$user?.role === 'admin' ? (item?.value ?? '') : ''}
												placement="top-start"
											> -->
											<img
												src={getModelIcon(item.label)}
												alt="Model"
												class="rounded-full size-5 flex items-center mr-2"
											/>
											<span class="text-xs">{item.label}</span>
											<!-- </Tooltip> -->
										</div>
										<!-- <div class="text-2xs ml-7 text-[#808080] leading-normal">
											{modelsInfo?.[item.label]?.description}
										</div> -->
									</div>
									<!-- {#if item.model.owned_by === 'ollama' && (item.model.ollama?.details?.parameter_size ?? '') !== ''}
										<div class="flex ml-1 items-center translate-y-[0.5px]">
											<Tooltip
												content={`${
													item.model.ollama?.details?.quantization_level
														? item.model.ollama?.details?.quantization_level + ' '
														: ''
												}${
													item.model.ollama?.size
														? `(${(item.model.ollama?.size / 1024 ** 3).toFixed(1)}GB)`
														: ''
												}`}
												className="self-end"
											>
												<span
													class=" text-xs font-medium text-gray-600 dark:text-gray-400 line-clamp-1"
													>{item.model.ollama?.details?.parameter_size ?? ''}</span
												>
											</Tooltip>
										</div>
									{/if} -->
								</div>

								<!-- {JSON.stringify(item.info)} -->

								<!-- {#if item.model.owned_by === 'openai'}
									<Tooltip content={`${'External'}`}>
										<div class="translate-y-[1px]">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="size-3"
											>
												<path
													fill-rule="evenodd"
													d="M8.914 6.025a.75.75 0 0 1 1.06 0 3.5 3.5 0 0 1 0 4.95l-2 2a3.5 3.5 0 0 1-5.396-4.402.75.75 0 0 1 1.251.827 2 2 0 0 0 3.085 2.514l2-2a2 2 0 0 0 0-2.828.75.75 0 0 1 0-1.06Z"
													clip-rule="evenodd"
												/>
												<path
													fill-rule="evenodd"
													d="M7.086 9.975a.75.75 0 0 1-1.06 0 3.5 3.5 0 0 1 0-4.95l2-2a3.5 3.5 0 0 1 5.396 4.402.75.75 0 0 1-1.251-.827 2 2 0 0 0-3.085-2.514l-2 2a2 2 0 0 0 0 2.828.75.75 0 0 1 0 1.06Z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
									</Tooltip>
								{/if} -->

								<!-- {#if item.model?.info?.meta?.description}
									<Tooltip
										content={`${marked.parse(
											sanitizeResponseContent(item.model?.info?.meta?.description).replaceAll(
												'\n',
												'<br>'
											)
										)}`}
									>
										<div class=" translate-y-[1px]">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
												/>
											</svg>
										</div>
									</Tooltip>
								{/if} -->

								<!-- {#if !$mobile && (item?.model?.info?.meta?.tags ?? []).length > 0}
									<div class="flex gap-0.5 self-center items-center h-full translate-y-[0.5px]">
										{#each item.model?.info?.meta.tags as tag}
											<Tooltip content={tag.name}>
												<div
													class=" text-xs font-bold px-1 rounded uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
												>
													{tag.name}
												</div>
											</Tooltip>
										{/each}
									</div>
								{/if} -->
							</div>
						</div>

						{#if value === item.value}
							<div class="ml-auto pl-2 pr-2 md:pr-0 text-lightGray-100 dark:text-customGray-100">
								<svg
									width="13"
									height="14"
									viewBox="0 0 9 10"
									fill="none"
									xmlns="http://www.w3.org/2000/svg"
								>
									<path
										d="M4.16004 6.27718C4.08868 6.27718 4.02088 6.24863 3.97093 6.19868L2.96115 5.1889C2.85768 5.08542 2.85768 4.91415 2.96115 4.81068C3.06463 4.7072 3.2359 4.7072 3.33937 4.81068L4.16004 5.63135L5.99405 3.79733C6.09753 3.69386 6.2688 3.69386 6.37227 3.79733C6.47575 3.90081 6.47575 4.07208 6.37227 4.17555L4.34915 6.19868C4.2992 6.24863 4.2314 6.27718 4.16004 6.27718Z"
										fill="currentColor"
									/>
								</svg>
							</div>
						{/if}
					</button>
				{:else}
					<div>
						<div class="block px-3 py-2 text-sm text-gray-700 dark:text-gray-100">
							{$i18n.t('No results found')}
						</div>
					</div>
				{/each}
				{#if hoveredItem}
					<div
						class="absolute px-3 py-1 left-full ml-1 top-0 w-52 p-2 rounded-xl border border-lightGray-400 bg-lightGray-550 dark:border-customGray-700 dark:bg-customGray-900 text-sm text-gray-800 dark:text-white z-50"
					>
						<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
							<p class="text-xs dark:text-customGray-100">
								{modelsInfo?.[hoveredItem?.label]?.description}
							</p>
						</div>
						{#if modelsInfo?.[hoveredItem?.label]?.organization}
							<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
								<p class="text-xs dark:text-customGray-100">
									{modelsInfo?.[hoveredItem?.label]?.organization}
								</p>
								<p class="text-2xs dark:text-white/50">{$i18n.t('Organization')}</p>
							</div>
						{/if}
						{#if modelsInfo?.[hoveredItem?.label]?.hosted_in}
							<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
								<p class="text-xs dark:text-customGray-100">{modelsInfo?.[hoveredItem?.label]?.hosted_in}</p>
								<p class="text-2xs dark:text-white/50">{$i18n.t('Hosted In')}</p>
							</div>
						{/if}

						<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
							<p class="text-xs dark:text-customGray-100">
								{#if modelsInfo?.[hoveredItem?.label]?.context_window}
									{modelsInfo?.[hoveredItem?.label]?.context_window}
								{:else}
									N/A
								{/if}
							</p>
							<p class="text-2xs dark:text-white/50">{$i18n.t('Context Window')}</p>
						</div>

						<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
							<p class="text-xs dark:text-customGray-100">
								{#if knowledgeCutoff}
									{knowledgeCutoff}
								{:else}
									N/A
								{/if}
							</p>
							<p class="text-2xs dark:text-white/50">{$i18n.t('Knowledge Cutoff')}</p>
						</div>

						<div class="py-1.5 text-xs dark:text-customGray-100 border-b dark:border-customGray-700 last:border-b-0">
							{#if modelsInfo?.[hoveredItem?.label]?.intelligence_score}
								<StarRating rating={modelsInfo?.[hoveredItem?.label]?.intelligence_score} />
							{:else}
								N/A
							{/if}
							<p class="text-2xs dark:text-white/50">{$i18n.t('Intelligence Score')}</p>
						</div>

						<div class="py-1.5 text-xs dark:text-customGray-100 border-b dark:border-customGray-700 last:border-b-0">
							{#if modelsInfo?.[hoveredItem?.label]?.speed}
								<SpeedRating rating={modelsInfo?.[hoveredItem?.label]?.speed} />
							{:else}
								N/A
							{/if}
							<p class="text-2xs dark:text-white/50">{$i18n.t('Speed')}</p>
						</div>

						{#if modelsInfo?.[hoveredItem?.label]?.multimodal}
							<div class="py-2.5 border-b dark:border-customGray-700 last:border-b-0">
								<p class="text-xs dark:text-customGray-100">{$i18n.t('Multimodal')}</p>
							</div>
						{/if}
						{#if modelsInfo?.[hoveredItem?.label]?.reasoning}
							<div class="py-2.5 border-b dark:border-customGray-700 last:border-b-0">
								<p class="text-xs dark:text-customGray-100">{$i18n.t('Reasoning')}</p>
							</div>
						{/if}
					</div>
				{/if}

				{#if !(searchValue.trim() in $MODEL_DOWNLOAD_POOL) && searchValue && ollamaVersion && $user.role === 'admin'}
					<Tooltip
						content={$i18n.t(`Pull "{{searchValue}}" from Ollama.com`, {
							searchValue: searchValue
						})}
						placement="top-start"
					>
						<button
							class="flex w-full line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-none transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer data-[highlighted]:bg-muted"
							on:click={() => {
								pullModelHandler();
							}}
						>
							<div class=" truncate">
								{$i18n.t(`Pull "{{searchValue}}" from Ollama.com`, { searchValue: searchValue })}
							</div>
						</button>
					</Tooltip>
				{/if}

				{#each Object.keys($MODEL_DOWNLOAD_POOL) as model}
					<div
						class="flex w-full justify-between font-medium select-none rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-none transition-all duration-75 rounded-lg cursor-pointer data-[highlighted]:bg-muted"
					>
						<div class="flex">
							<div class="-ml-2 mr-2.5 translate-y-0.5">
								<svg
									class="size-4"
									viewBox="0 0 24 24"
									fill="currentColor"
									xmlns="http://www.w3.org/2000/svg"
									><style>
										.spinner_ajPY {
											transform-origin: center;
											animation: spinner_AtaB 0.75s infinite linear;
										}
										@keyframes spinner_AtaB {
											100% {
												transform: rotate(360deg);
											}
										}
									</style><path
										d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
										opacity=".25"
									/><path
										d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
										class="spinner_ajPY"
									/></svg
								>
							</div>

							<div class="flex flex-col self-start">
								<div class="flex gap-1">
									<div class="line-clamp-1">
										Downloading "{model}"
									</div>

									<div class="flex-shrink-0">
										{'pullProgress' in $MODEL_DOWNLOAD_POOL[model]
											? `(${$MODEL_DOWNLOAD_POOL[model].pullProgress}%)`
											: ''}
									</div>
								</div>

								{#if 'digest' in $MODEL_DOWNLOAD_POOL[model] && $MODEL_DOWNLOAD_POOL[model].digest}
									<div class="-mt-1 h-fit text-[0.7rem] dark:text-gray-500 line-clamp-1">
										{$MODEL_DOWNLOAD_POOL[model].digest}
									</div>
								{/if}
							</div>
						</div>

						<div class="mr-2 ml-1 translate-y-0.5">
							<Tooltip content={$i18n.t('Cancel')}>
								<button
									class="text-gray-800 dark:text-gray-100"
									on:click={() => {
										cancelModelPullHandler(model);
									}}
								>
									<svg
										class="w-4 h-4 text-gray-800 dark:text-white"
										aria-hidden="true"
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										fill="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke="currentColor"
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18 17.94 6M18 18 6.06 6"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>

			<!-- {#if showTemporaryChatControl}
				<hr class="border-gray-50 dark:border-gray-800" />

				<div class="flex items-center mx-2 my-2">
					<button
						class="flex justify-between w-full font-medium line-clamp-1 select-none items-center rounded-button py-2 px-3 text-sm text-gray-700 dark:text-gray-100 outline-none transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer data-[highlighted]:bg-muted"
						on:click={async () => {
							temporaryChatEnabled.set(!$temporaryChatEnabled);
							await goto('/');
							const newChatButton = document.getElementById('new-chat-button');
							setTimeout(() => {
								newChatButton?.click();
							}, 0);

							// add 'temporary-chat=true' to the URL
							if ($temporaryChatEnabled) {
								history.replaceState(null, '', '?temporary-chat=true');
							} else {
								history.replaceState(null, '', location.pathname);
							}

							show = false;
						}}
					>
						<div class="flex gap-2.5 items-center">
							<ChatBubbleOval className="size-4" strokeWidth="2.5" />

							{$i18n.t(`Temporary Chat`)}
						</div>

						<div>
							<Switch state={$temporaryChatEnabled} />
						</div>
					</button>
				</div>
			{/if} -->

			<div class="hidden w-[42rem]" />
			<div class="hidden w-[32rem]" />
		</slot>
	</DropdownMenu.Content>
</DropdownMenu.Root>
