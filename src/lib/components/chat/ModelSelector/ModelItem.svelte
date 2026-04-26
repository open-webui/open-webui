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

	function companyLogo(id: string): 'anthropic' | 'mistral' | null {
		const s = (id ?? '').toLowerCase();
		if (s.includes('claude') || s.includes('haiku') || s.includes('sonnet') || s.includes('opus') || s.includes('medio') || s.includes('complex')) return 'anthropic';
		if (s.includes('mistral')) return 'mistral';
		return null;
	}

	function modelTier(id: string): { color: string; label: string } {
		const s = (id ?? '').toLowerCase();
		if (s.includes('opus'))                              return { color: '#16A34A', label: 'Opus' };
		if (s.includes('sonnet') || s.includes('medio') || s.includes('complex')) return { color: '#F59E0B', label: 'Sonnet' };
		if (s.includes('haiku') || s === 'haiku' || s.includes('default'))        return { color: '#EA580C', label: 'Haiku' };
		if (s.includes('mistral'))                           return { color: '#7C3AED', label: 'Mistral' };
		return { color: '#6B7280', label: '' };
	}

	export let selectedModelIdx: number = -1;
	export let item: any = {};
	export let index: number = -1;
	export let value: string = '';

	export let unloadModelHandler: (modelValue: string) => void = () => {};
	export let pinModelHandler: (modelId: string) => void = () => {};

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
</script>

<button
	role="option"
	aria-selected={value === item.value}
	aria-label={$i18n.t('Select {{modelName}} model', { modelName: item.label })}
	class="flex group/item w-full text-left font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl cursor-pointer data-highlighted:bg-muted {index ===
	selectedModelIdx
		? 'bg-gray-100 dark:bg-gray-800 group-hover:bg-transparent'
		: ''}"
	data-arrow-selected={index === selectedModelIdx}
	data-value={item.value}
	on:click={() => {
		onClick();
	}}
>
	<div class="flex flex-col flex-1 gap-1.5">
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

		<div class="flex items-center gap-2">
			<div class="flex items-center min-w-fit">
				<Tooltip
					content={$user?.role === 'admin'
						? (item?.value ?? '')
						: modelTier(item.value).label
							? `${modelTier(item.value).label} · ${modelTier(item.value).label === 'Haiku' ? 'Rápido y eficiente' : modelTier(item.value).label === 'Sonnet' ? 'Equilibrado' : modelTier(item.value).label === 'Opus' ? 'Máxima capacidad' : 'Alternativa EU'}`
							: ''}
					placement="top-start"
				>
					<div class="relative">
						{#if item.model?.info?.meta?.profile_image_url}
							<img
								src={item.model.info.meta.profile_image_url}
								alt={item.label}
								class="rounded-full size-5 object-cover"
								loading="lazy"
								on:error={(e) => { e.currentTarget.style.display='none'; }}
							/>
						{:else if companyLogo(item.value) === 'anthropic'}
							<!-- Anthropic logo -->
							<div class="size-5 rounded-full flex items-center justify-center" style="background:#CC785C">
								<svg viewBox="0 0 24 24" width="13" height="13" fill="white" xmlns="http://www.w3.org/2000/svg">
									<path d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-3.654 0H6.57L0 20h3.603l1.357-3.415h6.857L13.173 20h3.603l-6.603-16.48zM6.984 13.8l2.41-6.063 2.41 6.063H6.984z"/>
								</svg>
							</div>
						{:else if companyLogo(item.value) === 'mistral'}
							<!-- Mistral logo -->
							<div class="size-5 rounded-full flex items-center justify-center" style="background:#FF7000">
								<svg viewBox="0 0 24 24" width="13" height="13" fill="white" xmlns="http://www.w3.org/2000/svg">
									<path d="M3 3h4v4H3zm14 0h4v4h-4zM3 10h4v4H3zm7-7h4v4h-4zm0 14h4v4h-4zm7 0h4v4h-4zM3 17h4v4H3zm7-7h4v4h-4z"/>
								</svg>
							</div>
						{:else}
							<img
								src="/favicon.png"
								alt={item.label}
								class="rounded-full size-5 object-cover"
								loading="lazy"
							/>
						{/if}
						{#if modelTier(item.value).color}
							<span
								class="absolute -bottom-0.5 -right-0.5 size-2 rounded-full ring-1 ring-white dark:ring-gray-850"
								style="background:{modelTier(item.value).color}"
							/>
						{/if}
					</div>
				</Tooltip>
			</div>

			<div class="flex items-center">
				<Tooltip content={`${item.label} (${item.value})`} placement="top-start">
					<div class="line-clamp-1">
						{item.label}
					</div>
				</Tooltip>
			</div>

			<div class=" shrink-0 flex items-center gap-2">
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
								<span class=" text-xs font-medium text-gray-600 dark:text-gray-400 line-clamp-1"
									>{item.model.ollama?.details?.parameter_size ?? ''}</span
								>
							</Tooltip>
						</div>
					{/if}
					{#if item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
						<div class="flex items-center translate-y-[0.5px] px-0.5">
							<Tooltip
								content={`${$i18n.t('Unloads {{FROM_NOW}}', {
									FROM_NOW: dayjs(item.model.ollama?.expires_at * 1000).fromNow()
								})}`}
								className="self-end"
							>
								<div class=" flex items-center">
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>
							</Tooltip>
						</div>
					{/if}
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

	<div class="ml-auto pl-2 pr-1 flex items-center gap-1.5 shrink-0">
		{#if $user?.role === 'admin' && item.model.owned_by === 'ollama' && item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
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

		<ModelItemMenu
			bind:show={showMenu}
			model={item.model}
			{pinModelHandler}
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

		{#if value === item.value}
			<div>
				<Check className="size-3" />
			</div>
		{/if}
	</div>
</button>
