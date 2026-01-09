<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	export let webhook;
	export let expanded = false;

	export let onClick = () => {};
	export let onDelete = () => {};
	export let onUpdate = (changes: { name: string; profile_image_url: string }) => {};

	let name = webhook.name;
	let image = webhook.profile_image_url || '';

	// Notify parent when changes occur
	$: if (name !== webhook.name || image !== (webhook.profile_image_url || '')) {
		onUpdate({ name: name.trim() || webhook.name, profile_image_url: image });
	}

	let filesInputElement;
	let inputFiles;

	const handleImageUpload = () => {
		if (!inputFiles?.length) return;

		const reader = new FileReader();
		reader.onload = (event) => {
			const dataUrl = `${event.target?.result}`;
			const fileType = inputFiles[0]?.type;

			if (['image/gif', 'image/webp'].includes(fileType)) {
				image = dataUrl;
			} else {
				const tempImage = new Image();
				tempImage.src = dataUrl;
				tempImage.onload = () => {
					const canvas = document.createElement('canvas');
					const canvasSize = 100;
					canvas.width = canvasSize;
					canvas.height = canvasSize;

					const context = canvas.getContext('2d');
					const aspectRatio = tempImage.width / tempImage.height;
					const scaledWidth = aspectRatio > 1 ? canvasSize * aspectRatio : canvasSize;
					const scaledHeight = aspectRatio > 1 ? canvasSize : canvasSize / aspectRatio;
					const offsetX = (canvasSize - scaledWidth) / 2;
					const offsetY = (canvasSize - scaledHeight) / 2;

					context.drawImage(tempImage, offsetX, offsetY, scaledWidth, scaledHeight);
					image = canvas.toDataURL('image/webp', 0.8);
				};
			}
			inputFiles = null;
		};
		reader.readAsDataURL(inputFiles[0]);
	};

	const copyUrl = () => {
		navigator.clipboard.writeText(
			`${WEBUI_API_BASE_URL}/channels/webhooks/${webhook.id}/${webhook.token}`
		);
		toast.success($i18n.t('Copied'));
	};
</script>

<input
	bind:this={filesInputElement}
	bind:files={inputFiles}
	type="file"
	hidden
	accept="image/*"
	on:change={handleImageUpload}
/>

<div class="text-xs -mx-1">
	<!-- Row -->
	<button
		type="button"
		class="w-full flex items-center gap-3 px-3.5 py-3 hover:bg-gray-50 dark:hover:bg-gray-900 rounded-xl transition"
		on:click={onClick}
	>
		<img
			src={image || `${WEBUI_BASE_URL}/static/favicon.png`}
			class="rounded-full size-8 object-cover flex-shrink-0"
			alt=""
		/>
		<div class="flex-1 text-left min-w-0">
			<div class="font-medium text-gray-900 dark:text-white truncate">
				{name}
			</div>
			<div class="text-gray-500 text-xs">
				{$i18n.t('Created on {{date}}', {
					date: dayjs(webhook.created_at / 1000000).format('MMM D, YYYY')
				})}
				{#if webhook.user?.name}
					{$i18n.t('by {{name}}', { name: webhook.user.name })}
				{/if}
			</div>
		</div>
		<ChevronDown
			className="size-3.5 text-gray-400 transition-transform duration-200 {expanded
				? 'rotate-180'
				: ''}"
		/>
	</button>

	<!-- Expanded -->
	{#if expanded}
		<div class="mt-1 mb-3 px-3.5 py-3 border border-gray-100 dark:border-gray-850 rounded-2xl">
			<div class="flex items-center gap-3">
				<button
					type="button"
					class="shrink-0 rounded-xl overflow-hidden hover:opacity-80 transition"
					on:click={() => filesInputElement.click()}
				>
					<img
						src={image || `${WEBUI_BASE_URL}/static/favicon.png`}
						class="size-8 object-cover"
						alt=""
					/>
				</button>
				<div class="flex-1">
					<div class=" text-gray-500 text-xs">{$i18n.t('Name')}</div>
					<input
						type="text"
						class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700"
						bind:value={name}
						placeholder={$i18n.t('Webhook Name')}
					/>
				</div>
				<div class="flex items-center gap-1">
					<Tooltip content={$i18n.t('Copy URL')}>
						<button
							type="button"
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={copyUrl}
						>
							<Clipboard className="size-4 text-gray-500" />
						</button>
					</Tooltip>
					<Tooltip content={$i18n.t('Delete')}>
						<button
							type="button"
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={onDelete}
						>
							<GarbageBin className="size-4 text-gray-500" />
						</button>
					</Tooltip>
				</div>
			</div>
		</div>
	{/if}
</div>
