<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { copyToClipboard, sanitizeSvg } from '$lib/utils';

	import PanzoomContainer from './PanzoomContainer.svelte';
	import Tooltip from './Tooltip.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import Reset from '../icons/Reset.svelte';
	import Download from '../icons/Download.svelte';

	export let className = '';
	export let svg = '';
	export let content = '';

	let panzoomRef: PanzoomContainer;
	const resetPanZoomViewport = () => {
		panzoomRef?.reset();
	};

	const downloadAsSVG = () => {
		const svgBlob = new Blob([svg], { type: 'image/svg+xml' });
		saveAs(svgBlob, `diagram.svg`);
	};
</script>

<div class="relative {className}">
	<PanzoomContainer
		bind:this={panzoomRef}
		className="flex h-full max-h-full justify-center items-center"
	>
		{@html sanitizeSvg(svg)}
	</PanzoomContainer>

	{#if content}
		<div class=" absolute top-2.5 right-2.5">
			<div class="flex gap-1">
				<Tooltip content={$i18n.t('Download as SVG')}>
					<button
						class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
						on:click={() => {
							downloadAsSVG();
						}}
					>
						<Download className=" size-4" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Reset view')}>
					<button
						class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
						on:click={() => {
							resetPanZoomViewport();
						}}
					>
						<Reset className=" size-4" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Copy to clipboard')}>
					<button
						class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
						on:click={() => {
							copyToClipboard(content);
							toast.success($i18n.t('Copied to clipboard'));
						}}
					>
						<Clipboard className=" size-4" strokeWidth="1.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	{/if}
</div>
