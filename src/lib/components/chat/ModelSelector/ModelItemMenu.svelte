<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
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
		<div
			class="min-w-[210px] text-sm rounded-2xl p-1 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800"
		>
			{#if model?.preset || model?.info?.base_model_id ? model?.info?.user_id === $user?.id : $user?.role === 'admin'}
				<button
					type="button"
					class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
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
					<Pencil className="size-4" />

					<div class="flex items-center">{$i18n.t('Edit')}</div>
				</button>

				<hr class="border-gray-50 dark:border-gray-800/30 my-1" />
			{/if}

			<button
				type="button"
				aria-pressed={($settings?.pinnedModels ?? []).includes(model?.id)}
				class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
				on:click={(e) => {
					e.stopPropagation();
					e.preventDefault();

					pinModelHandler(model?.id);
					show = false;
				}}
			>
				{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
					<PinSlash />
				{:else}
					<Pin />
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
				class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
				on:click={(e) => {
					e.stopPropagation();
					e.preventDefault();

					copyLinkHandler();
					show = false;
				}}
			>
				<Link />

				<div class="flex items-center">{$i18n.t('Copy Link')}</div>
			</button>

			{#if $config?.features.enable_community_sharing}
				<hr class="border-gray-50 dark:border-gray-800/30 my-1" />

				<button
					type="button"
					class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
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
					<GlobeAlt className="size-4" />

					<div class="flex items-center">{$i18n.t('Community Reviews')}</div>
				</button>
			{/if}
		</div>
	</div>
</Dropdown>
