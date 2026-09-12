<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import EditPencil from '$lib/components/icons/EditPencil.svelte';
	import ArrowForward from '$lib/components/icons/ArrowForward.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let id: string;
	export let content: string;
	export let files: any[] = [];
	export let onSendNow: (id: string) => void;
	export let onEdit: (id: string) => void;
	export let onDelete: (id: string) => void;
</script>

<div class="flex items-center gap-2 px-2 py-1.5">
	<!-- Arrow forward icon -->
	<div class="shrink-0 text-gray-500">
		<ArrowForward className="size-3.5" />
	</div>

	<!-- Message content -->
	<div class="flex-1 min-w-0 flex items-center gap-2">
		{#if files.length > 0}
			<div class="flex items-center gap-1 shrink-0">
				{#each files as file}
					{#if file.type === 'image' || (file?.content_type ?? '').startsWith('image/')}
						{@const fileUrl =
							file.url?.startsWith('data') || file.url?.startsWith('http')
								? file.url
								: `${WEBUI_API_BASE_URL}/files/${file.url}${file?.content_type ? '/content' : ''}`}
						<div
							class="relative size-6 shrink-0 overflow-hidden rounded-lg border border-gray-100/60 bg-white/60 dark:border-white/[0.06] dark:bg-white/[0.025]"
						>
							<Image src={fileUrl} alt="" imageClassName="size-full object-cover" />
							{#if file.status === 'uploading'}
								<div
									class="absolute inset-0 flex items-center justify-center bg-white/75 text-gray-500 backdrop-blur-[1px] dark:bg-gray-950/70 dark:text-gray-300"
								>
									<Spinner className="size-3" />
								</div>
							{/if}
						</div>
					{:else}
						<div
							class="flex h-6 max-w-[9rem] items-center gap-1 rounded-lg border border-gray-100/60 bg-white/60 px-1.5 text-[0.6875rem] leading-none text-gray-500 dark:border-white/[0.06] dark:bg-white/[0.025] dark:text-gray-400"
						>
							{#if file.status === 'uploading'}
								<span class="shrink-0 text-gray-400 dark:text-gray-500">
									<Spinner className="size-3" />
								</span>
							{/if}
							<span class="max-w-[5rem] truncate">{file.name ?? 'file'}</span>
						</div>
					{/if}
				{/each}
			</div>
		{/if}

		{#if content}
			<p class="text-sm text-gray-600 dark:text-gray-300 truncate">{content}</p>
		{:else if files.length === 0}
			<p class="text-sm text-gray-400 dark:text-gray-500 truncate italic">
				{$i18n.t('Empty message')}
			</p>
		{/if}

		{#if files.some((file) => file.status === 'error')}
			<span class="shrink-0 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Upload failed')}
			</span>
		{/if}
	</div>

	<!-- Actions -->
	<div class="flex items-center gap-1 shrink-0">
		<!-- Send immediately -->
		<Tooltip
			content={files.some((file) => ['uploading', 'error'].includes(file.status))
				? $i18n.t('Waiting for upload')
				: $i18n.t('Send now')}
		>
			<button
				type="button"
				class="p-1 text-gray-400 transition-colors {files.some((file) =>
					['uploading', 'error'].includes(file.status)
				)
					? 'opacity-40 cursor-not-allowed'
					: 'hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'}"
				disabled={files.some((file) => ['uploading', 'error'].includes(file.status))}
				on:click={() => {
					if (!files.some((file) => ['uploading', 'error'].includes(file.status))) {
						onSendNow(id);
					}
				}}
				aria-label={files.some((file) => ['uploading', 'error'].includes(file.status))
					? $i18n.t('Waiting for upload')
					: $i18n.t('Send now')}
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
						d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18"
					/>
				</svg>
			</button>
		</Tooltip>

		<!-- Edit -->
		<Tooltip content={$i18n.t('Edit')}>
			<button
				type="button"
				class="p-1 text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
				on:click={() => onEdit(id)}
				aria-label={$i18n.t('Edit')}
			>
				<EditPencil className="size-3.5" />
			</button>
		</Tooltip>

		<!-- Delete -->
		<Tooltip content={$i18n.t('Delete')}>
			<button
				type="button"
				class="p-1 text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
				on:click={() => onDelete(id)}
				aria-label={$i18n.t('Delete')}
			>
				<GarbageBin className="size-3.5" />
			</button>
		</Tooltip>
	</div>
</div>
