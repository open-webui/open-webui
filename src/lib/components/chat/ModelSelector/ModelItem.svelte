<script lang="ts">
	import { marked } from 'marked';

	import { getContext, tick } from 'svelte';
	import dayjs from '$lib/dayjs';

	import { mobile, settings, user } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { copyToClipboard, sanitizeResponseContent } from '$lib/utils';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ModelItemMenu from './ModelItemMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import { toast } from 'svelte-sonner';
	import Tag from '$lib/components/icons/Tag.svelte';
	import Label from '$lib/components/icons/Label.svelte';

	const i18n = getContext('i18n');

	export let selectedModelIdx: number = -1;
	export let item: any = {};
	export let index: number = -1;
	export let value: string | null = '';
	export let selectedValues: string[] = [];
	export let compareEnabled = false;

	export let unloadModelHandler: (modelValue: string) => void = () => {};
	export let pinModelHandler: (modelId: string) => void = () => {};
	export let deleteModelHandler: (model: any) => void = () => {};
	export let selectionOnly = false;

	export let onClick: () => void = () => {};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	let showMenu = false;
	$: isSelected = compareEnabled ? selectedValues.includes(item.value) : value === item.value;
</script>

<button
	role="option"
	aria-selected={isSelected}
	aria-label={$i18n.t('Select {{modelName}} model', { modelName: item.label })}
	class="group/item flex h-8 w-full cursor-pointer select-none items-center rounded-xl px-2 text-left text-[13px] font-normal text-gray-700 outline-hidden transition-colors duration-75 hover:bg-gray-50/40 dark:text-gray-100 dark:hover:bg-gray-800/40 {index ===
		selectedModelIdx && !compareEnabled
		? 'bg-gray-50/70 dark:bg-gray-800/60'
		: ''} {isSelected ? 'bg-gray-50/70 dark:bg-gray-800/60' : ''}"
	data-arrow-selected={index === selectedModelIdx}
	data-value={item.value}
	on:click={() => {
		onClick();
	}}
>
	<div class="flex flex-1 flex-col gap-1.5 overflow-hidden">
		<!-- {#if (item?.model?.tags ?? []).length > 0}
			<div
				class="flex gap-0.5 self-center items-start h-full w-full translate-y-[0.5px] overflow-x-auto scrollbar-none"
			>
				{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
					<Tooltip content={tag.name} className="flex-shrink-0">
						<div
							class=" text-xs font-semibold px-1 rounded-sm uppercase bg-gray-500/20 text-gray-700 dark:text-gray-200"
						>
							{tag.name}
						</div>
					</Tooltip>
				{/each}
			</div>
		{/if} -->

		<div class="flex items-center gap-2 overflow-hidden">
			<div class="flex items-center min-w-fit">
				<Tooltip content={$user?.role === 'admin' ? (item?.value ?? '') : ''} placement="top-start">
					<img
						src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${item.model.id}&lang=${$i18n.language}`}
						alt={$i18n.t('{{modelName}} profile image', { modelName: item.label })}
						class="flex size-4 items-center rounded-full"
						loading="lazy"
						on:error={(e) => {
							e.currentTarget.src = '/favicon.png';
						}}
					/>
				</Tooltip>
			</div>

			<div class="flex min-w-0 items-center">
				<Tooltip content={`${item.label} (${item.value})`} placement="top-start">
					<div class="line-clamp-1">
						{item.label}
					</div>
				</Tooltip>
			</div>

			<div class="flex shrink-0 items-center gap-1.5">
				{#if item.model.owned_by === 'ollama'}
					{#if (item.model.ollama?.details?.parameter_size ?? '') !== ''}
						<div class="flex items-center translate-y-[0.5px]">
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
								<span class="line-clamp-1 text-[11px] font-normal text-gray-500 dark:text-gray-400"
									>{item.model.ollama?.details?.parameter_size ?? ''}</span
								>
							</Tooltip>
						</div>
					{/if}
				{/if}

				{#if item.model.loaded}
					<div class="flex items-center px-0.5">
						<Tooltip
							content={item.model.ollama?.expires_at &&
							new Date(item.model.ollama?.expires_at * 1000) > new Date()
								? `${$i18n.t('Unloads {{FROM_NOW}}', {
										FROM_NOW: dayjs(item.model.ollama?.expires_at * 1000).fromNow()
									})}`
								: `${$i18n.t('Loaded')}`}
							className="self-end"
						>
							<div class=" flex items-center">
								<span class="relative flex size-1.5">
									<span
										class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
									/>
									<span class="relative inline-flex size-1.5 rounded-full bg-green-500" />
								</span>
							</div>
						</Tooltip>
					</div>
				{/if}

				<!-- {JSON.stringify(item.info)} -->

				{#if (item?.model?.tags ?? []).length > 0}
					{#key item.model.id}
						<Tooltip elementId="tags-{item.model.id}">
							<div slot="tooltip" id="tags-{item.model.id}">
								{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
									<Tooltip content={tag.name} className="flex-shrink-0">
										<div class=" text-xs font-medium rounded-sm uppercase text-white">
											{tag.name}
										</div>
									</Tooltip>
								{/each}
							</div>

							<div class="translate-y-[1px]">
								<Tag />
							</div>
						</Tooltip>
					{/key}
				{/if}

				{#if item.model?.direct}
					<Tooltip content={`${$i18n.t('Direct')}`}>
						<div class="translate-y-[1px]">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-3"
							>
								<path
									fill-rule="evenodd"
									d="M2 2.75A.75.75 0 0 1 2.75 2C8.963 2 14 7.037 14 13.25a.75.75 0 0 1-1.5 0c0-5.385-4.365-9.75-9.75-9.75A.75.75 0 0 1 2 2.75Zm0 4.5a.75.75 0 0 1 .75-.75 6.75 6.75 0 0 1 6.75 6.75.75.75 0 0 1-1.5 0C8 10.35 5.65 8 2.75 8A.75.75 0 0 1 2 7.25ZM3.5 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</Tooltip>
				{:else if item.model.connection_type === 'external'}
					<Tooltip content={`${$i18n.t('External')}`}>
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
				{/if}

				{#if item.model?.info?.meta?.description}
					<Tooltip
						content={`${marked.parse(
							sanitizeResponseContent(item.model?.info?.meta?.description).replaceAll('\n', '<br>')
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
				{/if}
			</div>
		</div>
	</div>

	<div class="ml-auto flex shrink-0 items-center gap-1.5 pl-2">
		{#if !selectionOnly && $user?.role === 'admin' && item.model.loaded}
			<Tooltip
				content={`${$i18n.t('Eject')}`}
				className="flex-shrink-0 group-hover/item:opacity-100 opacity-0 "
			>
				<button
					class="flex"
					aria-label={$i18n.t('Eject model')}
					on:click={(e) => {
						e.preventDefault();
						e.stopPropagation();
						unloadModelHandler(item.value);
					}}
				>
					<ArrowUpTray className="size-3" />
				</button>
			</Tooltip>
		{/if}

		{#if !selectionOnly}
			<ModelItemMenu
				bind:show={showMenu}
				model={item.model}
				{pinModelHandler}
				{deleteModelHandler}
				copyLinkHandler={() => {
					copyLinkHandler(item.model);
				}}
			>
				<button
					aria-label={`${$i18n.t('More Options')}`}
					class="flex"
					on:click={(e) => {
						e.preventDefault();
						e.stopPropagation();
						showMenu = !showMenu;
					}}
				>
					<EllipsisHorizontal />
				</button>
			</ModelItemMenu>
		{/if}

		{#if isSelected}
			<div>
				<Check className="size-3" />
			</div>
		{/if}
	</div>
</button>
