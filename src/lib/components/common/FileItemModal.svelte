<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';

	export let file;
	export let show = false;

	export let edit = false;

	let enableFullContent = false;

	onMount(() => {
		console.log(file);

		if (file?.context === 'full') {
			enableFullContent = true;
		}
	});
</script>

<Modal bind:show size="md">
	<div class="font-primary px-6 py-5 w-full flex flex-col justify-center dark:text-gray-400">
		<div class=" pb-2">
			<div class="flex items-start justify-between">
				<div>
					<div class=" font-medium text-lg dark:text-gray-100">
						<a
							href={file.url ? (file.type === 'file' ? `${file.url}/content` : `${file.url}`) : '#'}
							target="_blank"
							class="hover:underline line-clamp-1"
						>
							{file?.name ?? 'File'}
						</a>
					</div>
				</div>

				<div>
					<button
						on:click={() => {
							show = false;
						}}
					>
						<XMark />
					</button>
				</div>
			</div>

			<div>
				<div class="flex flex-col md:flex-row gap-1 justify-between w-full">
					<div class=" flex flex-wrap text-sm gap-1 text-gray-500">
						{#if file.size}
							<div class="capitalize shrink-0">{formatFileSize(file.size)}</div>
							•
						{/if}

						{#if file?.file?.content}
							<div class="capitalize shrink-0">
								{getLineCount(file?.file?.content ?? '')} extracted lines
							</div>

							<div class="flex items-center gap-1 shrink-0">
								<Info />

								Formatting may be inconsistent from source.
							</div>
						{/if}
					</div>

					{#if edit}
						<div>
							<Tooltip
								content={enableFullContent
									? 'Inject the entire document as context for comprehensive processing.'
									: 'Default to segmented retrieval for focused and relevant content extraction.'}
							>
								<div class="flex items-center gap-1.5 text-xs">
									{#if enableFullContent}
										Use Entire Document
									{:else}
										Use Focused Retrieval
									{/if}
									<Switch
										bind:state={enableFullContent}
										on:change={(e) => {
											file.context = e.detail ? 'full' : undefined;
										}}
									/>
								</div>
							</Tooltip>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
			{file?.file?.content ?? 'No content'}
		</div>
	</div>
</Modal>
