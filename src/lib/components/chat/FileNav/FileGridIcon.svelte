<script lang="ts">
	import { downloadFileBlob, type FileEntry } from '$lib/apis/terminal';
	import { fileIconName } from './fileIcon';
	import Icon from './Icon.svelte';

	export let entry: FileEntry;
	export let path = '';
	export let terminalUrl = '';
	export let terminalKey = '';
	export let sessionId: string | undefined = undefined;
	export let itemCount: number | null = null;

	let imageUrl: string | null = null;
	let imageFailed = false;
	$: iconName = fileIconName(entry.name, entry.type);

	const observeImage = (node: HTMLElement) => {
		const extension = entry.name.split('.').pop()?.toLowerCase() ?? '';
		// shortcut: Bound automatic downloads until the terminal provides resized thumbnails.
		if (
			entry.type !== 'file' ||
			!terminalUrl ||
			entry.size === undefined ||
			entry.size > 5 * 1024 * 1024 ||
			!['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif', 'bmp', 'ico'].includes(extension)
		)
			return;

		const controller = new AbortController();
		let disposed = false;
		let objectUrl: string | null = null;
		const observer = new IntersectionObserver((observations) => {
			if (!observations.some((item) => item.isIntersecting)) return;
			observer.disconnect();
			void downloadFileBlob(terminalUrl, terminalKey, path, sessionId, controller.signal)
				.then((result) => {
					if (disposed || !result) return;
					objectUrl = URL.createObjectURL(result.blob);
					imageUrl = objectUrl;
				})
				.catch(() => {
					/* Keep the file icon when a preview is unavailable. */
				});
		});
		observer.observe(node);
		return {
			destroy() {
				disposed = true;
				observer.disconnect();
				controller.abort();
				if (objectUrl) URL.revokeObjectURL(objectUrl);
			}
		};
	};
</script>

<span
	use:observeImage
	class="flex h-11 w-full shrink-0 items-center justify-center"
	aria-hidden="true"
>
	{#if imageUrl && !imageFailed}
		<img
			src={imageUrl}
			alt=""
			draggable="false"
			decoding="async"
			class="max-h-10 max-w-12 rounded-sm object-contain shadow-sm"
			on:error={() => (imageFailed = true)}
		/>
	{:else if entry.type === 'directory'}
		<svg width="46" height="38" viewBox="0 0 72 58" fill="none">
			<path
				d="M4 10a5 5 0 0 1 5-5h17l7 7h30a5 5 0 0 1 5 5v30H4Z"
				class="fill-sky-500 dark:fill-sky-600"
			/>
			{#if itemCount !== null && itemCount > 0}
				<path d="M12 15h48v16H12Z" class="fill-sky-100 dark:fill-sky-200" />
				<path d="M9 18h54v14H9Z" fill="white" />
			{/if}
			<rect x="4" y="20" width="64" height="33" rx="5" class="fill-sky-400 dark:fill-sky-500" />
			<path d="M9 20.5h54" stroke="white" stroke-opacity="0.35" />
		</svg>
	{:else}
		<span
			class="relative flex h-10 w-8 items-center justify-center rounded-md border border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800"
		>
			<span
				class="absolute right-0 top-0 h-2.5 w-2.5 rounded-bl border-b border-l border-gray-200 bg-gray-50 dark:border-gray-600 dark:bg-gray-700"
			></span>
			<Icon
				name={iconName}
				size={20}
				strokeWidth={1.2}
				class={['image', 'svg-format', 'play', 'speaker'].includes(iconName)
					? 'text-violet-500 dark:text-violet-300'
					: ['pdf-logo', 'pptx-logo'].includes(iconName)
						? 'text-rose-500 dark:text-rose-300'
						: ['xlsx-logo', 'csv-logo'].includes(iconName)
							? 'text-emerald-600 dark:text-emerald-400'
							: 'text-slate-500 dark:text-slate-300'}
			/>
		</span>
	{/if}
</span>
