<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import PinSlash from '$lib/components/icons/PinSlash.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[180px]';

	export let onDownload = (type) => {};
	export let onDelete = () => {};
	export let onPin = null;
	export let isPinned = false;

	export let onCopyLink = null;
	export let onCopyToClipboard = null;

	export let onChange = () => {};
</script>

<Dropdown
	bind:show
	align="end"
	sideOffset={6}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[180px]">
			<DropdownSub>
				<button
					slot="trigger"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				>
					<Download strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Download')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('txt');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('md');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.md)')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('pdf');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
				</button>
			</DropdownSub>

			{#if onCopyLink || onCopyToClipboard}
				<DropdownSub>
					<button
						slot="trigger"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					>
						<Share strokeWidth="2" />
						<div class="flex items-center">{$i18n.t('Share')}</div>
					</button>

					{#if onCopyLink}
						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								onCopyLink();
							}}
						>
							<Link />
							<div class="flex items-center">{$i18n.t('Copy link')}</div>
						</button>
					{/if}

					{#if onCopyToClipboard}
						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								onCopyToClipboard();
							}}
						>
							<DocumentDuplicate strokeWidth="2" />
							<div class="flex items-center">{$i18n.t('Copy to clipboard')}</div>
						</button>
					{/if}
				</DropdownSub>
			{/if}

			{#if onPin}
				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onPin();
						show = false;
					}}
				>
					{#if isPinned}
						<PinSlash />
						<div class="flex items-center">{$i18n.t('Unpin')}</div>
					{:else}
						<Pin />
						<div class="flex items-center">{$i18n.t('Pin to Sidebar')}</div>
					{/if}
				</button>
			{/if}

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
