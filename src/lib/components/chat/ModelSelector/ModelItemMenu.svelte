<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';

	import { getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;
	export let model;

	export let pinModelHandler: (modelId: string) => void = () => {};
	export let copyLinkHandler: Function = () => {};

	export let onClose: Function = () => {};
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<Tooltip content={$i18n.t('More')} className=" group-hover/item:opacity-100  opacity-0">
			<slot />
		</Tooltip>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		strategy="fixed"
		class="w-full max-w-[180px] text-sm rounded-xl px-1 py-1.5 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		sideOffset={-2}
		side="bottom"
		align="end"
		transition={flyAndScale}
	>
		<button
			type="button"
			class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
			on:click={(e) => {
				e.stopPropagation();
				e.preventDefault();

				pinModelHandler(model?.id);
				show = false;
			}}
		>
			{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
				<EyeSlash />
			{:else}
				<Eye />
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
			class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2"
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
	</DropdownMenu.Content>
</DropdownMenu.Root>
