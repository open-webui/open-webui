<script lang="ts">
	import DOMPurify from 'dompurify';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { marked, type Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';
	import { showArtifacts, hideInline, showControls, codeBlockTitles } from '$lib/stores';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { chats } from '$lib/stores';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import MarkdownInlineTokens from '$lib/components/chat/Messages/Markdown/MarkdownInlineTokens.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import AlertRenderer, { alertComponent } from './AlertRenderer.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';

	import Source from './Source.svelte';
	import { settings } from '$lib/stores';

	const dispatch = createEventDispatcher();

	export let id: string;
	export let tokens: Token[];
	export let top = true;
	export let attributes = {};

	export let save = false;

	export let onTaskClick: Function = () => {};
	export let onSourceClick: Function = () => {};

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};

	const getSeededColor = (inValue: string): string => {
    // Define an array of 16 colors (you can customize this list)
    const colors = [
        '#FF5733', '#33FF57', '#3357FF', '#F1C40F',
        '#8E44AD', '#1ABC9C', '#E74C3C', '#16A085',
        '#2ECC71', '#9B59B6', '#F39C12', '#D35400',
        '#34495E', '#7F8C8D', '#27AE60', '#2980B9'
    ];

    // Hash the input 'inValue' to a number between 0 and 15
    let hash = 0;
    for (let i = 0; i < inValue.length; i++) {
        hash = (hash << 5) - hash + inValue.charCodeAt(i);
        hash = hash & hash; // Convert to 32bit integer
    }

    // Map the hash value to one of the 16 colors
    const colorIndex = Math.abs(hash) % 16;

    return colors[colorIndex];
};
const getTokenTitle = (content: string): string | undefined => {

	return codeBlockTitles[content];
}

	const exportTableToCSVHandler = (token, tokenIdx = 0) => {
		console.log('Exporting table to CSV');

		// Extract header row text and escape for CSV.
		const header = token.header.map((headerCell) => `"${headerCell.text.replace(/"/g, '""')}"`);

		// Create an array for rows that will hold the mapped cell text.
		const rows = token.rows.map((row) =>
			row.map((cell) => {
				// Map tokens into a single text
				const cellContent = cell.tokens.map((token) => token.text).join('');
				// Escape double quotes and wrap the content in double quotes
				return `"${cellContent.replace(/"/g, '""')}"`;
			})
		);

		// Combine header and rows
		const csvData = [header, ...rows];

		// Join the rows using commas (,) as the separator and rows using newline (\n).
		const csvContent = csvData.map((row) => row.join(',')).join('\n');

		// Log rows and CSV content to ensure everything is correct.
		console.log(csvData);
		console.log(csvContent);

		// To handle Unicode characters, you need to prefix the data with a BOM:
		const bom = '\uFEFF'; // BOM for UTF-8

		// Create a new Blob prefixed with the BOM to ensure proper Unicode encoding.
		const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=UTF-8' });

		// Use FileSaver.js's saveAs function to save the generated CSV file.
		saveAs(blob, `table-${id}-${tokenIdx}.csv`);
	};
</script>
<style>
	.clickable-div {
	  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out; /* Keep background and shadow transitions */
	}
  
	.clickable-div:hover {
	  background-color: rgba(0, 0, 0, 0.3); /* Darkens the background color on hover */
	  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); /* Adds a shadow effect on hover */
	  animation: swell 0.3s ease-in-out forwards; /* Apply the swell animation */
	}
  
	.clickable-div {
	  animation: shrink 0.3s ease-in-out forwards; /* Add animation to shrink on un-hover */
	}
  
	@keyframes swell {
	  from {
		transform: scale(1);
	  }
	  to {
		transform: scale(1.025);
	  }
	}
  
	@keyframes shrink {
	  from {
		transform: scale(1.025);
	  }
	  to {
		transform: scale(1);
	  }
	}
  </style>
  
  
  

<!-- {JSON.stringify(tokens)} -->
{#each tokens as token, tokenIdx (tokenIdx)}
	{#if token.type === 'hr'}
		<hr class=" border-gray-100 dark:border-gray-850" />
	{:else if token.type === 'heading'}
		<svelte:element this={headerComponent(token.depth)} dir="auto">
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-h`} tokens={token.tokens} {onSourceClick} />
		</svelte:element>
	{:else if token.type === 'code'}
		{#if token.raw.includes('```')}
			{#if !$showArtifacts || ($showArtifacts && $hideInline) || token?.lang === ''}
				<CodeBlock
					id={`${id}-${tokenIdx}`}
					collapsed={$settings?.collapseCodeBlocks ?? false}
				{token}
					lang={token?.lang ?? ''}
					code={revertSanitizedResponseContent(token?.text ?? '')}
					{attributes}
				{save}
					onCode={(value) => {
						dispatch('code', value);
					}}
					onSave={(value) => {
						dispatch('update', {
							raw: token.raw,
							oldContent: token.text,
							newContent: value
						});
					}}
				/>
				{:else}

				<div class="clickable-div" style="transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out; cursor: pointer; user-select: none; position: relative; width: full; padding: 0.5rem; border-radius: 15px; background-color: rgba(0, 0, 0, 0.2); display: flex;"
				on:click={() => {
					window.parent.postMessage({ type: 'FROM_MDT', data: token.text }, '*');
					}}>
				<div 
					id="codeBlock" 
					style="width: 5rem; height: 5rem; display: flex; justify-content: center; align-items: center; background-color: transparent; border-radius: 5px; cursor: pointer; position: relative;" 

				>
				<div style="position: absolute; color: {getSeededColor(token?.lang ?? 'Code')}; background-color: black; font-size: 12pt; font-weight: bold; z-index: 1; border-radius: 8px; padding-left: 10px; padding-right: 10px;">
					{token?.lang === '' ? '</>' : token?.lang ?? '</>'} <!-- Call the getCodeText function here -->
				</div>
				

					<!-- SVG Icon -->
					<svg fill="#000000" viewBox="0 0 32 32" id="icon" xmlns="http://www.w3.org/2000/svg">
					<g id="SVGRepo_bgCarrier" stroke-width="0"></g>
					<g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g>
					<g id="SVGRepo_iconCarrier">
						<defs>
						<style>.cls-1{fill:none;}</style>
						</defs>
						<title>script</title>
						<polygon points="18.83 26 21.41 23.42 20 22 16 26 20 30 21.42 28.59 18.83 26" stroke="lightgray" stroke-width="1"></polygon>
						<polygon points="27.17 26 24.59 28.58 26 30 30 26 26 22 24.58 23.41 27.17 26" stroke="lightgray" stroke-width="1"></polygon>
						<path d="M14,28H8V4h8v6a2.0058,2.0058,0,0,0,2,2h6v6h2V10a.9092.9092,0,0,0-.3-.7l-7-7A.9087.9087,0,0,0,18,2H8A2.0058,2.0058,0,0,0,6,4V28a2.0058,2.0058,0,0,0,2,2h6ZM18,4.4,23.6,10H18Z" stroke="lightgray" stroke-width="1"></path>
						<rect id="_Transparent_Rectangle_" data-name="<Transparent Rectangle>" class="cls-1" width="32" height="32"></rect>
					</g>
					</svg>
					</div>
					
					<div style="margin-left: 1rem; height:100%">
						<h3 style="margin-top:0.5rem; margin-bottom: 0px; padding-bottom: 0px">{getTokenTitle(token.text) ?? (token?.lang ?? 'Code')}</h3>
						{#if token.raw.endsWith('```')}
						<p style="margin-top: 0px; padding-top: 0px">Click to open artifact</p>
						{:else}
						<div class="flex items-center gap-1">
							<Spinner className="size-4" />
							<span class="shimmer">Writing code for artifact...</span>
						</div>
						{/if}
					</div>

					</div>
			  {/if}
		{:else}
			{token.text}
		{/if}
	{:else if token.type === 'table'}
		<div class="relative w-full group">
			<div class="scrollbar-hidden relative overflow-x-auto max-w-full rounded-lg">
				<table
					class=" w-full text-sm text-left text-gray-500 dark:text-gray-400 max-w-full rounded-xl"
				>
					<thead
						class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 border-none"
					>
						<tr class="">
							{#each token.header as header, headerIdx}
								<th
									scope="col"
									class="px-3! py-1.5! cursor-pointer border border-gray-100 dark:border-gray-850"
									style={token.align[headerIdx] ? '' : `text-align: ${token.align[headerIdx]}`}
								>
									<div class="gap-1.5 text-left">
										<div class="shrink-0 break-normal">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-header-${headerIdx}`}
												tokens={header.tokens}
												{onSourceClick}
											/>
										</div>
									</div>
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each token.rows as row, rowIdx}
							<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
								{#each row ?? [] as cell, cellIdx}
									<td
										class="px-3! py-1.5! text-gray-900 dark:text-white w-max border border-gray-100 dark:border-gray-850"
										style={token.align[cellIdx] ? '' : `text-align: ${token.align[cellIdx]}`}
									>
										<div class="break-normal">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-row-${rowIdx}-${cellIdx}`}
												tokens={cell.tokens}
												{onSourceClick}
											/>
										</div>
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<div class=" absolute top-1 right-1.5 z-20 invisible group-hover:visible">
				<Tooltip content={$i18n.t('Export to CSV')}>
					<button
						class="p-1 rounded-lg bg-transparent transition"
						on:click={(e) => {
							e.stopPropagation();
							exportTableToCSVHandler(token, tokenIdx);
						}}
					>
						<ArrowDownTray className=" size-3.5" strokeWidth="1.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	{:else if token.type === 'blockquote'}
		{@const alert = alertComponent(token)}
		{#if alert}
			<AlertRenderer {token} {alert} />
		{:else}
			<blockquote dir="auto">
				<svelte:self id={`${id}-${tokenIdx}`} tokens={token.tokens} {onTaskClick} {onSourceClick} />
			</blockquote>
		{/if}
	{:else if token.type === 'list'}
		{#if token.ordered}
			<ol start={token.start || 1}>
				{#each token.items as item, itemIdx}
					<li dir="auto" class="text-start">
						{#if item?.task}
							<input
								class=" translate-y-[1px] -translate-x-1"
								type="checkbox"
								checked={item.checked}
								on:change={(e) => {
									onTaskClick({
										id: id,
										token: token,
										tokenIdx: tokenIdx,
										item: item,
										itemIdx: itemIdx,
										checked: e.target.checked
									});
								}}
							/>
						{/if}

						<svelte:self
							id={`${id}-${tokenIdx}-${itemIdx}`}
							tokens={item.tokens}
							top={token.loose}
							{onTaskClick}
							{onSourceClick}
						/>
					</li>
				{/each}
			</ol>
		{:else}
			<ul>
				{#each token.items as item, itemIdx}
					<li dir="auto" class="text-start">
						{#if item?.task}
							<input
								class=" translate-y-[1px] -translate-x-1"
								type="checkbox"
								checked={item.checked}
								on:change={(e) => {
									onTaskClick({
										id: id,
										token: token,
										tokenIdx: tokenIdx,
										item: item,
										itemIdx: itemIdx,
										checked: e.target.checked
									});
								}}
							/>
						{/if}

						<svelte:self
							id={`${id}-${tokenIdx}-${itemIdx}`}
							tokens={item.tokens}
							top={token.loose}
							{onTaskClick}
							{onSourceClick}
						/>
					</li>
				{/each}
			</ul>
		{/if}
	{:else if token.type === 'details'}
		<Collapsible
			title={token.summary}
			open={$settings?.expandDetails ?? false}
			attributes={token?.attributes}
			className="w-full space-y-1"
			dir="auto"
		>
			<div class=" mb-1.5" slot="content">
				<svelte:self
					id={`${id}-${tokenIdx}-d`}
					tokens={marked.lexer(token.text)}
					attributes={token?.attributes}
					{onTaskClick}
					{onSourceClick}
				/>
			</div>
		</Collapsible>
	{:else if token.type === 'html'}
		{@const html = DOMPurify.sanitize(token.text)}
		{#if html && html.includes('<video')}
			{@html html}
		{:else if token.text.includes(`<iframe src="${WEBUI_BASE_URL}/api/v1/files/`)}
			{@html `${token.text}`}
		{:else if token.text.includes(`<source_id`)}
			<Source {id} {token} onClick={onSourceClick} />
		{:else}
			{token.text}
		{/if}
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
		></iframe>
	{:else if token.type === 'paragraph'}
		<p dir="auto">
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{onSourceClick}
			/>
		</p>
	{:else if token.type === 'text'}
		{#if top}
			<p dir="auto">
				{#if token.tokens}
					<MarkdownInlineTokens id={`${id}-${tokenIdx}-t`} tokens={token.tokens} {onSourceClick} />
				{:else}
					{unescapeHtml(token.text)}
				{/if}
			</p>
		{:else if token.tokens}
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{onSourceClick}
			/>
		{:else}
			{unescapeHtml(token.text)}
		{/if}
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={token?.displayMode ?? false} />
		{/if}
	{:else if token.type === 'blockKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={token?.displayMode ?? false} />
		{/if}
	{:else if token.type === 'space'}
		<div class="my-2" />
	{:else}
		{console.log('Unknown token', token)}
	{/if}
{/each}
