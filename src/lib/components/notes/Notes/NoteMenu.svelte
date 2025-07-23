<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, slide } from 'svelte/transition';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[180px]';

	export let onDownload = (type) => {};
	export let onDelete = () => {};

	export let onCopyLink = null;
	export let onCopyToClipboard = null;

	export let onChange = () => {};
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
			sideOffset={6}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				>
					<Download strokeWidth="2" />

					<div class="flex items-center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					class="w-full rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
					transition={flyAndScale}
					sideOffset={8}
					align="end"
				>
					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
						on:click={() => {
							onDownload('txt');
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
						on:click={() => {
							onDownload('md');
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.md)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
						on:click={() => {
							onDownload('pdf');
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>

			{#if onCopyLink || onCopyToClipboard}
				<DropdownMenu.Sub>
					<DropdownMenu.SubTrigger
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					>
						<Share strokeWidth="2" />

						<div class="flex items-center">{$i18n.t('Share')}</div>
					</DropdownMenu.SubTrigger>
					<DropdownMenu.SubContent
						class="w-full rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
						transition={flyAndScale}
						sideOffset={8}
						align="end"
					>
						{#if onCopyLink}
							<DropdownMenu.Item
								class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								on:click={() => {
									onCopyLink();
								}}
							>
								<Link />
								<div class="flex items-center">{$i18n.t('Copy link')}</div>
							</DropdownMenu.Item>
						{/if}

						{#if onCopyToClipboard}
							<DropdownMenu.Item
								class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								on:click={() => {
									onCopyToClipboard();
								}}
							>
								<DocumentDuplicate strokeWidth="2" />
								<div class="flex items-center">{$i18n.t('Copy to clipboard')}</div>
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.SubContent>
				</DropdownMenu.Sub>
			{/if}

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
