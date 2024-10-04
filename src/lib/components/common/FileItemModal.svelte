<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';

	export let item;
	export let show = false;

	export let edit = false;

	let enableFullContent = false;

	onMount(() => {
		console.log(item);

		if (item?.context === 'full') {
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
							href={item.url ? (item.type === 'file' ? `${item.url}/content` : `${item.url}`) : '#'}
							target="_blank"
							class="hover:underline line-clamp-1"
						>
							{item?.name ?? 'File'}
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
				<div class="flex flex-col items-center md:flex-row gap-1 justify-between w-full">
					<div class=" flex flex-wrap text-sm gap-1 text-gray-500">
						{#if item.size}
							<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
							•
						{/if}

						{#if item?.file?.data?.content}
							<div class="capitalize shrink-0">
								{getLineCount(item?.file?.data?.content ?? '')} extracted lines
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
									? 'Inject the entire document as context for comprehensive processing, this is recommended for complex queries.'
									: 'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'}
							>
								<div class="flex items-center gap-1.5 text-xs">
									{#if enableFullContent}
										Using Entire Document
									{:else}
										Using Focused Retrieval
									{/if}
									<Switch
										bind:state={enableFullContent}
										on:change={(e) => {
											item.context = e.detail ? 'full' : undefined;
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
			{item?.file?.data?.content ?? 'No content'}
		</div>
	</div>
</Modal>
