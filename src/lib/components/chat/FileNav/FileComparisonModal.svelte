<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { readComparisonSource } from '$lib/apis/terminal';
	import DiffEditorModal from '$lib/components/common/DiffEditorModal.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FileCompare from './FileCompare.svelte';

	export let files: [
		{ name: string; path: string; size?: number },
		{ name: string; path: string; size?: number }
	];
	export let baseUrl: string;
	export let apiKey: string;
	export let chatId: string | null;
	export let onClose: () => void;

	const i18n = getContext<any>('i18n');
	const opener =
		typeof document !== 'undefined' && document.activeElement instanceof HTMLElement
			? document.activeElement
			: null;
	// The caller keys this controller by its captured comparison session.
	const sourceFiles = files.map((file) => ({ ...file }));
	const connection = { baseUrl, apiKey, chatId };
	const documentComparison = sourceFiles.some(({ path }) =>
		/\.(pdf|docx?|xlsx?|pptx?|odt|ods|odp|rtf)$/i.test(path)
	);
	let content: { initialContent: string; proposedContent: string } | null = null;
	let loading = true;
	let error = '';
	let controller: AbortController | null = null;
	let generation = 0;
	let closed = false;

	const cancel = () => {
		generation++;
		controller?.abort();
	};
	const close = () => {
		closed = true;
		cancel();
		onClose();
	};
	const read = async () => {
		cancel();
		const request = new AbortController();
		controller = request;
		const current = generation;
		try {
			const texts = await Promise.all(
				sourceFiles.map(async (file) => {
					try {
						return await readComparisonSource(
							connection.baseUrl,
							connection.apiKey,
							file.path,
							request.signal,
							connection.chatId ?? undefined,
							file.size
						);
					} catch (cause) {
						request.signal.throwIfAborted();
						throw new Error(
							`${file.path}: ${$i18n.t(cause instanceof Error ? cause.message : 'Could not read file.')}`
						);
					}
				})
			);
			request.signal.throwIfAborted();
			if (closed || generation !== current)
				throw new DOMException('Comparison closed', 'AbortError');
			return { initialContent: texts[0], proposedContent: texts[1] };
		} catch (cause) {
			request.abort();
			throw cause;
		}
	};
	const load = async () => {
		loading = true;
		error = '';
		try {
			content = await read();
		} catch (cause) {
			if (!closed) error = cause instanceof Error ? cause.message : String(cause);
		} finally {
			if (!closed) loading = false;
		}
	};
	onMount(() => {
		if (!documentComparison) void load();
	});
	onDestroy(() => {
		closed = true;
		cancel();
		setTimeout(() => {
			if (opener?.isConnected) opener.focus();
		}, 0);
	});
	const preventSave = (event: KeyboardEvent) => {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
			event.preventDefault();
			event.stopPropagation();
		}
	};
</script>

{#if content}
	<DiffEditorModal
		show={true}
		mode="review"
		title={$i18n.t('Compare files')}
		initialContent={content.initialContent}
		proposedContent={content.proposedContent}
		leftFile={sourceFiles[0]}
		rightFile={sourceFiles[1]}
		onRefresh={read}
		onClose={close}
	/>
{:else}
	<Modal
		show={true}
		ariaLabel={$i18n.t('Compare files')}
		size="full"
		containerClassName="p-2 sm:p-4"
		className="h-[calc(100dvh-2rem)] overflow-hidden rounded-2xl bg-white dark:bg-gray-900 !border-0"
		onRequestClose={close}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="flex h-full min-h-0 flex-col text-xs" on:keydown|capture={preventSave}>
			{#if documentComparison}
				<div class="h-full min-h-0">
					<FileCompare
						paths={[sourceFiles[0].path, sourceFiles[1].path]}
						baseUrl={connection.baseUrl}
						apiKey={connection.apiKey}
						chatId={connection.chatId}
						onClose={close}
					/>
				</div>
			{:else}
				<div class="flex h-full min-h-0 flex-col text-xs">
					<header class="flex shrink-0 items-center justify-between gap-3 px-5 pt-4 pb-2">
						<h2 class="font-medium">{$i18n.t('Compare files')}</h2>
						<button
							type="button"
							class="shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-white"
							aria-label={$i18n.t('Close')}
							on:click|stopPropagation={close}><XMark className="size-4" /></button
						>
					</header>
					<div class="grid grid-cols-2 gap-4 px-4 py-2">
						{#each sourceFiles as file}
							<Tooltip
								content={file.path}
								allowHTML={false}
								className="min-w-0 rounded-lg bg-gray-50/70 px-3 py-2 text-gray-500 dark:bg-white/[0.03]"
							>
								<p class="truncate font-medium">{file.name}</p>
							</Tooltip>
						{/each}
					</div>
					{#if loading}
						<div class="flex flex-1 items-center justify-center gap-2 text-gray-500" role="status">
							<Spinner className="size-4" />{$i18n.t('Loading...')}
						</div>
					{:else if error}
						<p class="px-5 py-2 break-words text-red-600" role="alert">{error}</p>
						<button
							type="button"
							class="mx-5 mt-2 self-start rounded-lg bg-gray-100 dark:bg-gray-850 px-2.5 h-7"
							on:click={load}>{$i18n.t('Retry')}</button
						>
					{/if}
				</div>
			{/if}
		</div>
	</Modal>
{/if}
