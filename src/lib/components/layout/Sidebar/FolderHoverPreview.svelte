<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { LinkPreview } from 'bits-ui';
	import { getFolderById, getSharedFolderChats } from '$lib/apis/folders';
	import { models } from '$lib/stores';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FolderIcon from './icons/Folder.svelte';
	import EditPencil from './icons/EditPencil.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	const i18n: any = getContext('i18n');

	export let folder;
	export let isWritable = false;
	export let onEdit = () => {};

	let details: { data?: { model_ids?: string[]; files?: unknown[] } } | null = null;
	let total: number | null = null;
	let loading = true;

	$: modelNames = (details?.data?.model_ids ?? []).map(
		(id) => $models.find((model) => model.id === id)?.name ?? id
	);
	$: files = details?.data?.files ?? [];

	onMount(async () => {
		const [loadedFolder, chats] = await Promise.all([
			getFolderById(localStorage.token, folder.id).catch(() => null),
			getSharedFolderChats(localStorage.token, folder.id, { page: 1 }).catch(() => null)
		]);
		details = loadedFolder;
		total = chats?.total ?? null;
		loading = false;
	});
</script>

<LinkPreview.Portal>
	<LinkPreview.Content
		class="z-[9999] hidden w-[20rem] max-w-[calc(100vw-1.5rem)] max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-2xl bg-white text-[0.8125rem] font-normal text-gray-900 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 md:block dark:bg-gray-850 dark:text-gray-100 dark:ring-white/10"
		side="right"
		align="start"
		sideOffset={12}
	>
		<div class="space-y-1.5 px-3 py-2">
			<div class="flex items-center gap-2 leading-5">
				<div class="shrink-0 text-gray-500 dark:text-gray-400">
					{#if folder.meta?.icon}
						<Emoji className="size-3.5" shortCode={folder.meta.icon} />
					{:else}
						<FolderIcon className="size-3.5" />
					{/if}
				</div>
				<div class="min-w-0 break-words">{folder.name}</div>
			</div>
			<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
				<ChatBubble className="size-3.5 shrink-0" />
				{#if loading}
					<Spinner className="size-3" />
				{:else if total !== null}
					<span>{total.toLocaleString()} {$i18n.t(total === 1 ? 'Chat' : 'Chats')}</span>
				{:else}
					<span>{$i18n.t('Something went wrong :/')}</span>
				{/if}
				{#if !folder.shared && (folder.unread_count ?? 0) > 0}
					<span>·</span>
					<span>{folder.unread_count.toLocaleString()} {$i18n.t('Unread')}</span>
				{/if}
			</div>
		</div>

		{#if modelNames.length || files.length || folder.shared}
			<div class="space-y-1.5 border-t border-gray-50/60 px-3 py-2 dark:border-gray-800/25">
				{#if folder.shared}
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Shared')}{folder.owner_name ? ` · ${folder.owner_name}` : ''}
					</div>
				{/if}
				{#if modelNames.length}
					<div class="flex items-start gap-2">
						<Sparkles className="mt-0.5 size-3.5 shrink-0 text-gray-500 dark:text-gray-400" />
						<div class="min-w-0 break-words" title={$i18n.t('Default Model')}>
							{modelNames.join(', ')}
						</div>
					</div>
				{/if}
				{#if files.length}
					<div class="flex items-center gap-2">
						<Document className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400" />
						<span>
							{$i18n.t('Knowledge')} · {files.length.toLocaleString()}
							{$i18n.t(files.length === 1 ? 'File' : 'Files')}
						</span>
					</div>
				{/if}
			</div>
		{/if}

		{#if isWritable}
			<div class="border-t border-gray-50/60 p-1 dark:border-gray-800/25">
				<button
					type="button"
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] transition hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
					on:click={onEdit}
				>
					<EditPencil className="size-3.5 text-gray-500 dark:text-gray-400" />
					{$i18n.t('Edit Folder')}
				</button>
			</div>
		{/if}
	</LinkPreview.Content>
</LinkPreview.Portal>
