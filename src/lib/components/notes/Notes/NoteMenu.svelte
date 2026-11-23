<script lang="ts">
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import PinSlash from '$lib/components/icons/PinSlash.svelte';
	import CloudArrowUp from '$lib/components/icons/CloudArrowUp.svelte';
	import Bold from '$lib/components/icons/Bold.svelte';
	import FolderIcon from '$lib/components/layout/Sidebar/icons/Folder.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import { folders } from '$lib/stores';
	import EditPencilIcon from '$lib/components/layout/Sidebar/icons/EditPencil.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let show = false;
	export let className = 'max-w-[11.25rem]';

	export let onDownload = (type) => {};
	export let onAccess: (() => void) | null = null;
	export let onRename: (() => void) | null = null;
	export let onMove: ((folderId: string | null) => void) | null = null;
	/** The note's current folder, for the Move submenu. */
	export let folderId: string | null = null;
	export let onDelete: (() => void) | null = () => {};
	export let onPin = null;
	export let isPinned = false;
	export let onUploadFiles = null;
	export let showAutoFormat = false;
	export let autoFormat = true;

	export let onCopyLink = null;
	export let onCopyToClipboard = null;

	export let onChange = () => {};
</script>

<Dropdown
	closeOnSelect
	bind:show
	align="end"
	sideOffset={6}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[11.25rem]">
			{#if onAccess}
				<button
					type="button"
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => onAccess?.()}
				>
					<LockClosed className="size-3.5" />
					<div class="flex items-center">{$i18n.t('Access')}</div>
				</button>
			{/if}

			{#if onRename}
				<button
					type="button"
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => onRename?.()}
				>
					<EditPencilIcon className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Rename')}</div>
				</button>
			{/if}

			{#if onMove && (folderId || $folders.length > 0)}
				<DropdownSub contentClass="select-none z-50 max-h-52 overflow-y-auto scrollbar-hidden">
					<button
						slot="trigger"
						class="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					>
						<FolderIcon className="size-3.5" />
						<div class="flex items-center">{$i18n.t('Move')}</div>
					</button>

					{#if folderId}
						<button
							class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
							on:click={() => onMove?.(null)}
						>
							<div class="flex items-center">{$i18n.t('No folder')}</div>
						</button>
					{/if}
					{#each [...$folders].sort((a, b) => b.updated_at - a.updated_at) as folder (folder.id)}
						<button
							class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
							disabled={folder.id === folderId}
							on:click={() => onMove?.(folder.id)}
						>
							<div class="shrink-0"><FolderIcon className="size-3.5" /></div>
							<div class="min-w-0 flex-1 truncate text-left">{folder?.name ?? 'Folder'}</div>
							{#if folder.id === folderId}<Check className="size-3! shrink-0" />{/if}
						</button>
					{/each}
				</DropdownSub>
			{/if}

			{#if showAutoFormat}
				<Tooltip
					className="w-full"
					content={$i18n.t(
						'Format Markdown as you type and paste. Turn off to keep Markdown characters and paste plain text. Existing formatting is preserved.'
					)}
				>
					<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
					<div
						class="select-none flex h-[1.6875rem] items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-base-50/60 dark:hover:bg-base-800/60"
						on:click={(e) => e.preventDefault()}
					>
						<Bold className="size-3.5 shrink-0" strokeWidth="2" />
						<span class="flex-1">{$i18n.t('Formatting')}</span>
						<Switch bind:state={autoFormat} ariaLabel={$i18n.t('Formatting')} />
					</div>
				</Tooltip>
				<hr class="border-base-100 dark:border-base-800" />
			{/if}
			<DropdownSub contentClass="select-none z-50">
				<button
					slot="trigger"
					class="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
				>
					<Download className="size-3.5" strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Download')}</div>
				</button>

				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onDownload('txt');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
				</button>

				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onDownload('md');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.md)')}</div>
				</button>

				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onDownload('pdf');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
				</button>
			</DropdownSub>

			{#if onUploadFiles}
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onUploadFiles();
					}}
				>
					<CloudArrowUp className="size-3.5" strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Upload files')}</div>
				</button>
			{/if}

			{#if onCopyLink || onCopyToClipboard}
				<DropdownSub contentClass="select-none z-50">
					<button
						slot="trigger"
						class="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					>
						<Share className="size-3.5" strokeWidth="2" />
						<div class="flex items-center">{$i18n.t('Share')}</div>
					</button>

					{#if onCopyLink}
						<button
							class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
							on:click={() => {
								onCopyLink();
							}}
						>
							<Link className="size-3.5" />
							<div class="flex items-center">{$i18n.t('Copy link')}</div>
						</button>
					{/if}

					{#if onCopyToClipboard}
						<button
							class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
							on:click={() => {
								onCopyToClipboard();
							}}
						>
							<DocumentDuplicate className="size-3.5" strokeWidth="2" />
							<div class="flex items-center">{$i18n.t('Copy to clipboard')}</div>
						</button>
					{/if}
				</DropdownSub>
			{/if}

			{#if onPin}
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onPin();
					}}
				>
					{#if isPinned}
						<PinSlash className="size-3.5" />
						<div class="flex items-center">{$i18n.t('Unpin')}</div>
					{:else}
						<Pin className="size-3.5" />
						<div class="flex items-center">{$i18n.t('Pin to Sidebar')}</div>
					{/if}
				</button>
			{/if}

			{#if onDelete}
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-base-900 dark:hover:text-base-100"
					on:click={() => {
						onDelete?.();
					}}
				>
					<GarbageBin className="size-3.5" />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</button>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
