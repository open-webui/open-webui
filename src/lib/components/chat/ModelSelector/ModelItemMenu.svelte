<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import PinSlash from '$lib/components/icons/PinSlash.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import { config, settings, user } from '$lib/stores';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let model;

	export let pinModelHandler: (modelId: string) => void = () => {};
	export let copyLinkHandler: Function = () => {};
	export let deleteModelHandler: Function = () => {};

	export let onClose: Function = () => {};
</script>

<Dropdown
	bind:show
	align="end"
	sideOffset={-2}
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip
		content={$i18n.t('More')}
		className={($settings?.highContrastMode ?? false)
			? ''
			: 'group-hover/item:opacity-100 opacity-0'}
	>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[210px] z-[9999999]">
			{#if model?.preset || model?.info?.base_model_id ? model?.info?.user_id === $user?.id : $user?.role === 'admin'}
				<button
					type="button"
					class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
					on:click={(e) => {
						e.stopPropagation();
						e.preventDefault();

						goto(
							model?.preset || model?.info?.base_model_id
								? `/workspace/models/edit?id=${encodeURIComponent(model?.id ?? '')}`
								: `/admin/settings/models?id=${encodeURIComponent(model?.id ?? '')}`
						);
						show = false;
					}}
				>
					<Pencil className="size-3.5" />

					<div class="flex items-center">{$i18n.t('Edit')}</div>
				</button>

				{#if $user?.role === 'admin' && model?.owned_by === 'ollama'}
					<button
						type="button"
						class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
						on:click={(e) => {
							e.stopPropagation();
							e.preventDefault();

							deleteModelHandler(model);
							show = false;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
							/>
						</svg>

						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				{/if}

				<hr class="border-gray-50 dark:border-gray-800/30 mx-1 my-0.5" />
			{/if}

			<button
				type="button"
				aria-pressed={($settings?.pinnedModels ?? []).includes(model?.id)}
				class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
				on:click={(e) => {
					e.stopPropagation();
					e.preventDefault();

					pinModelHandler(model?.id);
					show = false;
				}}
			>
				{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
					<PinSlash className="size-3.5" />
				{:else}
					<Pin className="size-3.5" />
				{/if}

				<div class="flex items-center">
					{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
						{$i18n.t('Hide from Sidebar')}
					{:else}
						{$i18n.t('Keep in Sidebar')}
					{/if}
				</div>
			</button>

			<button
				type="button"
				class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
				on:click={(e) => {
					e.stopPropagation();
					e.preventDefault();

					copyLinkHandler();
					show = false;
				}}
			>
				<Link className="size-3.5" />

				<div class="flex items-center">{$i18n.t('Copy Link')}</div>
			</button>

			{#if $config?.features.enable_community_sharing}
				<hr class="border-gray-50 dark:border-gray-800/30 mx-1 my-0.5" />

				<button
					type="button"
					class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
					on:click={(e) => {
						e.stopPropagation();
						e.preventDefault();

						window.open(
							`https://openwebui.com/models?q=${encodeURIComponent(model?.id ?? '')}`,
							'_blank'
						);
						show = false;
					}}
				>
					<GlobeAlt className="size-3.5" />

					<div class="flex items-center">{$i18n.t('Community Reviews')}</div>
				</button>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
