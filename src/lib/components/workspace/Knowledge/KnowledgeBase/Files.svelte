<script lang="ts">
	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { capitalizeFirstLetter, formatFileSize } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let knowledge = null;
	export let selectedFileId = null;
	export let files = [];

	export let onClick = (fileId) => {};
	export let onDelete = (fileId) => {};

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
	{#each files as file (file?.id ?? file?.itemId ?? file?.tempId)}
		{@const fileStatus = file?.data?.status}
		{@const isInFlight =
			file?.status === 'uploading' || fileStatus === 'pending' || fileStatus === 'processing'}
		{@const isFailed = fileStatus === 'failed'}
		{@const statusTooltip = getStatusTooltip(file)}
		<div
			class=" flex cursor-pointer w-full px-1.5 py-0.5 bg-transparent dark:hover:bg-gray-850/50 hover:bg-white rounded-xl transition {selectedFileId
				? ''
				: 'hover:bg-gray-100 dark:hover:bg-gray-850'}"
		>
			<button
				class="relative group flex items-center gap-1 rounded-xl p-2 text-left flex-1 justify-between {isFailed
					? 'text-red-500 dark:text-red-400'
					: ''}"
				type="button"
				on:click={async () => {
					console.log('[Knowledge file]', {
						id: file?.id,
						name: file?.name ?? file?.meta?.name,
						status: file?.data?.status ?? file?.status,
						started_at: file?.data?.started_at
							? new Date(file.data.started_at * 1000).toISOString()
							: undefined,
						task_id: file?.data?.task_id,
						task_position: file?.data?.task_position,
						error: file?.data?.error,
						raw: file
					});
					if (isInFlight || !file?.id) return;
					onClick(file.id);
				}}
			>
				<div class="">
					<div class="flex gap-2 items-center line-clamp-1">
						<div class="shrink-0">
							{#if isInFlight || isFailed}
								<Tooltip content={statusTooltip} placement="top-start">
									{#if isInFlight}
										<Spinner className="size-3.5" />
									{:else}
										<DocumentPage className="size-3.5" />
									{/if}
								</Tooltip>
							{:else}
								<DocumentPage className="size-3.5" />
							{/if}
						</div>

						<div class="line-clamp-1 text-sm">
							{file?.name ?? file?.meta?.name}
							{#if file?.meta?.size}
								<span class="text-xs text-gray-500">{formatFileSize(file?.meta?.size)}</span>
							{/if}
						</div>
					</div>
				</div>

				<div class="flex items-center gap-2 shrink-0">
					{#if file?.updated_at}
						<Tooltip content={dayjs(file.updated_at * 1000).format('LLLL')}>
							<div>
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
					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => {
								onDelete(file?.id ?? file?.tempId);
							}}
						>
							<XMark />
						</button>
					</Tooltip>
				</div>
			{/if}
		</div>
	{/each}
</div>
