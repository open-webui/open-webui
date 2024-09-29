<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';

	export let file;
	export let show = false;

	onMount(() => {
		console.log(file);
	});
</script>

<Modal bind:show size="md">
	<div class="font-primary px-6 py-5 w-full flex flex-col justify-center dark:text-gray-400">
		<div class="flex items-start justify-between pb-2">
			<div>
				<div class=" font-medium text-lg line-clamp-1 dark:text-gray-100">
					{file?.name ?? 'File'}
				</div>

				<div>
					<div class=" flex text-sm gap-1 text-gray-500">
						{#if file.size}
							<div class="capitalize">{formatFileSize(file.size)}</div>
							•
						{/if}

						{#if file.content}
							<div class="capitalize">{getLineCount(file.content)} extracted lines</div>

							<div class="flex items-center gap-1">
								<Info />

								Formatting may be inconsistent from source.
							</div>
						{/if}
					</div>
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

		<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
			{file?.content ?? 'No content'}
		</div>
	</div>
</Modal>
