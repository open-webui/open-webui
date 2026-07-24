<script lang="ts">
	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { capitalizeFirstLetter, formatFileSize } from '$lib/utils';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import DirectoryRow from './DirectoryRow.svelte';

	export let knowledge = null;
	export let selectedFileId = null;
	export let files = [];
	export let directories = [];

	export let onClick = (fileId) => {};
	export let onDelete = (fileId) => {};
	export let onRename = (fileId: string, name: string) => {};
	export let onNavigateDirectory = (directoryId: string) => {};
	export let onRenameDirectory = (id: string, name: string) => {};
	export let onDeleteDirectory = (id: string) => {};
	export let onMoveFileToDirectory = (fileId: string, directoryId: string) => {};
	export let onMoveDirectoryToDirectory = (dirId: string, targetDirectoryId: string) => {};

	let editingFileId: string | null = null;
	let editName = '';
	let editInput: HTMLInputElement;

	const startRename = (file: any) => {
		editingFileId = file?.id ?? file?.tempId;
		editName = file?.name ?? file?.meta?.name ?? '';
		setTimeout(() => editInput?.select(), 0);
	};

	const submitRename = () => {
		if (editingFileId && editName.trim()) {
			onRename(editingFileId, editName.trim());
		}
		editingFileId = null;
	};

	const cancelRename = () => {
		editingFileId = null;
	};

	/** Build the HTML tooltip for files that are pending, processing, or failed. */
	function getStatusTooltip(file: any): string {
		// Local upload-in-progress item — data is not yet populated from server
		if (file?.status === 'uploading') {
			// If the SSE stream has already delivered a server-side status (e.g.
			// 'processing' once docling picks up the job), show that instead of
			// the generic "Uploading…" so the tooltip stays meaningful.
			const serverStatus = file?.data?.status;
			if (!serverStatus || serverStatus === 'pending') {
				return '<strong>Uploading…</strong>';
			}
			// fall through: real server status available, show it below
		}

		const status = file?.data?.status;
		if (!status || status === 'completed') return '';

		const parts: string[] = [];

		if (status === 'pending') {
			parts.push('<strong>Queued for processing</strong>');
		} else if (status === 'processing') {
			parts.push('<strong>Processing…</strong>');
		} else if (status === 'failed') {
			parts.push('<strong style="color:#f87171">Processing failed</strong>');
		}

		// started_at is written by process_file() just before loader.load()
		if (file?.data?.started_at) {
			parts.push(`Started: ${dayjs(file.data.started_at * 1000).fromNow()}`);
		} else if (status === 'pending' && file?.created_at) {
			parts.push(`Uploaded: ${dayjs(file.created_at * 1000).fromNow()}`);
		}

		// Docling-specific fields written by the status_callback during polling
		if (file?.data?.task_position != null) {
			parts.push(`Queue position: ${file.data.task_position}`);
		}
		if (file?.data?.task_id) {
			parts.push(`Task ID: ${String(file.data.task_id).slice(0, 8)}…`);
		}

		if (status === 'failed' && file?.data?.error) {
			parts.push(`<span style="color:#f87171">${file.data.error}</span>`);
		}

		return parts.join('<br>');
	}
</script>

<div class=" max-h-full flex flex-col w-full gap-[0.5px]">
	<!-- Directories first -->
	{#each directories as dir (dir.id)}
		<DirectoryRow
			directory={dir}
			writeAccess={knowledge?.write_access}
			onNavigate={(id) => onNavigateDirectory(id)}
			onRename={(id, name) => onRenameDirectory(id, name)}
			onDelete={(id) => onDeleteDirectory(id)}
			onFileDrop={(fileId, directoryId) => onMoveFileToDirectory(fileId, directoryId)}
			onDirDrop={(dirId, targetId) => onMoveDirectoryToDirectory(dirId, targetId)}
		/>
	{/each}

	<!-- Files -->
	{#each files as file (file?.id ?? file?.itemId ?? file?.tempId)}
		{@const fileStatus = file?.data?.status}
		{@const isInFlight =
			file?.status === 'uploading' || fileStatus === 'pending' || fileStatus === 'processing'}
		{@const isFailed = fileStatus === 'failed'}
		{@const statusTooltip = getStatusTooltip(file)}
		<div
			class=" flex cursor-pointer w-full px-2 bg-transparent dark:hover:bg-gray-850/50 hover:bg-white rounded-xl transition {selectedFileId
				? ''
				: 'hover:bg-gray-100 dark:hover:bg-gray-850'}"
			draggable="true"
			on:dragstart={(e) => {
				const fileId = file?.id ?? file?.tempId;
				if (fileId) {
					e.dataTransfer?.setData('application/x-kb-file-move', JSON.stringify({ fileId }));
				}
			}}
		>
			<div class="flex items-center">
				{#if file?.status === 'uploading' && (!file?.data?.status || file?.data?.status === 'pending')}
					<!-- No file ID yet — show spinner with status tooltip, no link -->
					<Tooltip content={statusTooltip} placement="top-start">
						<div class="p-1">
							<Spinner className="size-3.5" />
						</div>
					</Tooltip>
				{:else if isInFlight || isFailed}
					<!-- File exists but still processing / failed — link to PDF, carry status tooltip -->
					<Tooltip content={statusTooltip} placement="top-start">
						<button
							class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition {isFailed
								? 'text-red-500 dark:text-red-400'
								: ''}"
							type="button"
							on:click={() => {
								let fileId = file?.id ?? file?.tempId;
								if (fileId) window.open(`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content`, '_blank');
							}}
						>
							{#if isInFlight}
								<Spinner className="size-3.5" />
							{:else}
								<DocumentPage className="size-3.5" />
							{/if}
						</button>
					</Tooltip>
				{:else}
					<Tooltip content={$i18n.t('Open file')}>
						<button
							class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => {
								let fileId = file?.id ?? file?.tempId;
								window.open(`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content`, '_blank');
							}}
						>
							<DocumentPage className="size-3.5" />
						</button>
					</Tooltip>
				{/if}
			</div>

			<button
				class="relative group flex items-center gap-1 rounded-xl p-2 text-left flex-1 justify-between {isFailed
					? 'text-red-500 dark:text-red-400'
					: ''}"
				type="button"
				on:click={async () => {
					if (editingFileId) return;
					if (isInFlight || !file?.id) return;
					onClick(file.id);
				}}
				on:dblclick={() => {
					if (knowledge?.write_access) startRename(file);
				}}
			>
				<div>
					<div class="flex gap-2 items-center line-clamp-1">
						{#if editingFileId === (file?.id ?? file?.tempId)}
							<!-- svelte-ignore a11y-autofocus -->
							<input
								bind:this={editInput}
								bind:value={editName}
								class="text-xs w-full bg-transparent border-none outline-hidden"
								on:keydown={(e) => {
									if (e.key === 'Enter') submitRename();
									if (e.key === 'Escape') cancelRename();
									if (e.key === ' ') e.stopPropagation();
								}}
								on:keyup={(e) => {
									if (e.key === ' ') e.stopPropagation();
								}}
								on:blur={submitRename}
								on:click={(e) => e.stopPropagation()}
								autofocus
							/>
						{:else}
							<div class="line-clamp-1 text-xs">
								{file?.name ?? file?.meta?.name}
								{#if file?.meta?.size}
									<span class="text-[11px] text-gray-500">{formatFileSize(file?.meta?.size)}</span>
								{/if}
							</div>
						{/if}
					</div>
				</div>

				<div class="flex items-center gap-2 shrink-0">
					{#if file?.updated_at}
						<Tooltip content={dayjs(file.updated_at * 1000).format('LLLL')}>
							<div class="text-xs text-gray-400">
								{dayjs(file.updated_at * 1000).fromNow()}
							</div>
						</Tooltip>
					{/if}

					{#if file?.user}
						<Tooltip
							content={file?.user?.email ?? $i18n.t('Deleted User')}
							className="flex shrink-0"
							placement="top-start"
						>
							<div class="shrink-0 text-gray-500">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										file?.user?.name ?? file?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>
					{/if}
				</div>
			</button>

			{#if knowledge?.write_access}
				<div class="flex items-center">
					<Dropdown align="end" sideOffset={4}>
						<button
							class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
						>
							<EllipsisHorizontal className="size-3.5" />
						</button>

						<div slot="content">
							<DropdownMenu className="min-w-[140px] z-[9999999]">
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs transition hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => {
										startRename(file);
									}}
								>
									<Pencil className="size-3.5" />
									{$i18n.t('Rename')}
								</button>
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs transition hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => {
										let fileId = file?.id ?? file?.tempId;
										window.open(`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content`, '_blank');
									}}
								>
									<Download className="size-3.5" />
									{$i18n.t('Download')}
								</button>
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs transition hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => {
										onDelete(file?.id ?? file?.tempId);
									}}
								>
									<GarbageBin className="size-3.5" />
									{$i18n.t('Delete')}
								</button>
							</DropdownMenu>
						</div>
					</Dropdown>
				</div>
			{/if}
		</div>
	{/each}
</div>
