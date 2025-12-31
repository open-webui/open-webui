<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MarkdownInlineTokens from './MarkdownInlineTokens.svelte';
	import { copyToClipboard } from '$lib/utils';
	import { settings } from '$lib/stores';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	const i18n = getContext('i18n');

	export let show = false;
	export let token: any;
	export let id: string;
	export let tokenIdx: number = 0;
	export let done = true;
	export let sourceIds: string[] = [];
	export let onSourceClick: Function = () => {};

	const exportTableToCSV = () => {
		// Extract header row text and escape for CSV
		const header = token.header.map(
			(headerCell: any) => `"${headerCell.text.replace(/"/g, '""')}"`
		);

		// Create an array for rows that will hold the mapped cell text
		const rows = token.rows.map((row: any[]) =>
			row.map((cell) => {
				const cellText = cell?.text ?? '';
				return `"${cellText.replace(/"/g, '""')}"`;
			})
		);

		// Combine header and rows into a single CSV string
		const csv = [header.join(','), ...rows.map((row: string[]) => row.join(','))].join('\n');

		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
		saveAs(blob, `table-${id}-${tokenIdx}.csv`);
	};
</script>

<Modal bind:show size="xl" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-title-4 text-gray-900 dark:text-white">
				{$i18n.t('Full Table View')}
			</h3>
			<div class="flex items-center gap-2">
				<!-- Copy button -->
				<Tooltip content={$i18n.t('Copy')}>
					<button
						class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={() => copyToClipboard(token.raw.trim(), null, $settings?.copyFormatted ?? false)}
					>
						<Clipboard className="size-4" strokeWidth="1.5" />
					</button>
				</Tooltip>

				<!-- Export to CSV button -->
				<Tooltip content={$i18n.t('Export to CSV')}>
					<button
						class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={exportTableToCSV}
					>
						<Download className="size-4" strokeWidth="1.5" />
					</button>
				</Tooltip>

				<!-- Close button -->
				<button
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => (show = false)}
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>

		<!-- Full table -->
		<div class="overflow-auto max-h-[70vh] border border-gray-100 dark:border-gray-850 rounded-lg">
			<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-100 dark:bg-gray-800 dark:text-gray-400 sticky top-0"
				>
					<tr>
						{#each token.header as header, headerIdx}
							<th
								scope="col"
								class="px-3 py-2 border-b border-gray-200 dark:border-gray-700"
								style={token.align[headerIdx] ? `text-align: ${token.align[headerIdx]}` : ''}
							>
								<MarkdownInlineTokens
									id={`${id}-modal-header-${headerIdx}`}
									tokens={header.tokens}
									{done}
									{sourceIds}
									{onSourceClick}
								/>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each token.rows as row, rowIdx}
						<tr class="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850">
							{#each row ?? [] as cell, cellIdx}
								<td
									class="px-3 py-2 text-gray-900 dark:text-white {token.rows.length - 1 === rowIdx
										? ''
										: 'border-b border-gray-100 dark:border-gray-800'}"
									style={token.align[cellIdx] ? `text-align: ${token.align[cellIdx]}` : ''}
								>
									<MarkdownInlineTokens
										id={`${id}-modal-row-${rowIdx}-${cellIdx}`}
										tokens={cell.tokens}
										{done}
										{sourceIds}
										{onSourceClick}
									/>
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</Modal>
