<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Spinner from './Spinner.svelte';
	import { getFileById } from '$lib/apis/files';

	export let item;
	export let show = false;
	export let edit = false;

	let isPDF = false;
	let isAudio = false;
	let loading = false;

	$: isPDF =
		item?.meta?.content_type === 'application/pdf' ||
		(item?.name && item?.name.toLowerCase().endsWith('.pdf'));

	$: isAudio =
		(item?.meta?.content_type ?? '').startsWith('audio/') ||
		(item?.name && item?.name.toLowerCase().endsWith('.mp3')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.wav')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.ogg')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.m4a')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.webm'));

	const loadContent = async () => {
		if (item?.type === 'file') {
			loading = true;

			const file = await getFileById(localStorage.token, item.id).catch((e) => {
				console.error('Error fetching file:', e);
				return null;
			});

			if (file) {
				item.file = file || {};
			}
			loading = false;
		}

		await tick();
	};

	$: if (show) {
		loadContent();
	}

</script>

<Modal bind:show size="lg">
	<div class="font-primary px-4.5 py-3.5 w-full flex flex-col justify-center dark:text-gray-400">
		<div class=" pb-2">
			<div class="flex items-start justify-between">
				<div>
					<div class=" font-medium text-lg dark:text-gray-100">
						<a
							href="#"
							class="hover:underline line-clamp-1"
							on:click|preventDefault={() => {
								if (!isPDF && item.url) {
									window.open(
										item.type === 'file' ? `${item.url}/content` : `${item.url}`,
										'_blank'
									);
								}
							}}
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
						<div class=" flex flex-wrap text-xs gap-1 text-gray-500">
							{#if item.size}
								<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<div class="max-h-[75vh] overflow-auto">
				{#if !loading}
					{#if isPDF}
						<iframe
							title={item?.name}
							src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full h-[70vh] border-0 rounded-lg"
						/>
					{:else}
						{#if isAudio}
							<audio
								src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full border-0 rounded-lg mb-2"
							controls
							playsinline
						/>
					{/if}

					{#if item?.file?.data}
						<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
							{(item?.file?.data?.content ?? '').trim() || 'No content'}
						</div>
					{/if}
				{/if}
			{:else}
				<div class="flex items-center justify-center py-6">
					<Spinner className="size-5" />
				</div>
			{/if}
		</div>
	</div>
</Modal>
