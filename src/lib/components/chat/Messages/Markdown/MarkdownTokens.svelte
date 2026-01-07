<script lang="ts">
	import { decode } from 'html-entities';
	import DOMPurify from 'dompurify';

	import { marked, type Token } from 'marked';
	import { unescapeHtml } from '$lib/utils';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { settings } from '$lib/stores';

	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import MarkdownInlineTokens from '$lib/components/chat/Messages/Markdown/MarkdownInlineTokens.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import AlertRenderer, { alertComponent } from './AlertRenderer.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import Source from './Source.svelte';
	import HtmlToken from './HTMLToken.svelte';

	export let id: string;
	export let tokens: Token[];
	export let top = true;
	export let attributes = {};

	export let done = true;

	export let save = false;
	export let preview = false;

	export let editCodeBlock = true;
	export let topPadding = false;

	export let onSave: Function = () => {};
	export let onUpdate: Function = () => {};
	export let onPreview: Function = () => {};

	export let onTaskClick: Function = () => {};
	export let onSourceClick: Function = () => {};

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};

	const normalizeTimestampText = (text: string) =>
		text.replace(/(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})\.\d+(?:Z)?/, '$1');
	
	const normalizeTokens = (tokens = []) =>
		tokens.map((token) => {
			const updated = { ...token };
			if (updated.text) {
				updated.text = normalizeTimestampText(updated.text);
			}
			if (updated.raw) {
				updated.raw = normalizeTimestampText(updated.raw);
			} else if (updated.text) {
				updated.raw = updated.text;
			}
			if (Array.isArray(updated.tokens)) {
				updated.tokens = normalizeTokens(updated.tokens);
			}
			return updated;
		});

</script>

<!-- {JSON.stringify(tokens)} -->
{#each tokens as token, tokenIdx (tokenIdx)}
	{#if token.type === 'hr'}
		<hr class=" border-gray-100 dark:border-gray-850" />
	{:else if token.type === 'heading'}
		<svelte:element this={headerComponent(token.depth)} dir="auto">
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-h`}
				tokens={token.tokens}
				{done}
				{onSourceClick}
			/>
		</svelte:element>
	{:else if token.type === 'code'}
		{#if token.raw.includes('```')}
			<CodeBlock
				id={`${id}-${tokenIdx}`}
				collapsed={$settings?.collapseCodeBlocks ?? false}
				{token}
				lang={token?.lang ?? ''}
				code={token?.text ?? ''}
				{attributes}
				{save}
				{preview}
				edit={editCodeBlock}
				stickyButtonsClassName={topPadding ? 'top-7' : 'top-0'}
				onSave={(value) => {
					onSave({
						raw: token.raw,
						oldContent: token.text,
						newContent: value
					});
				}}
				{onUpdate}
				{onPreview}
			/>
		{:else}
			{token.text}
		{/if}
	{:else if token.type === 'table'}
		<div class="relative w-full group mb-2">
			<div class="scrollbar relative overflow-x-auto overflow-y-auto max-w-full max-h-96">
				<table
					class=" w-full text-sm text-left text-gray-500 dark:text-gray-400 max-w-full rounded-xl"
				>
					<thead
						class="text-xs text-gray-700 uppercase bg-white dark:bg-gray-900 dark:text-gray-400 border-none sticky top-0 z-10"
					>
						<tr class="">
							{#each token.header as header, headerIdx}
								<th
									scope="col"
									class="px-2.5! py-2! cursor-pointer border-b border-gray-100! dark:border-gray-800!"
									style={token.align[headerIdx] ? '' : `text-align: ${token.align[headerIdx]}`}
								>
									<div class="gap-1.5 text-left">
										<div class="shrink-0 break-normal">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-header-${headerIdx}`}
												tokens={normalizeTokens(header.tokens)}
												{done}
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
							<tr class="bg-white dark:bg-gray-900 text-xs">
								{#each row ?? [] as cell, cellIdx}
									<td
										class="px-3! py-2! text-gray-900 dark:text-white w-max {token.rows.length -
											1 ===
										rowIdx
											? ''
											: 'border-b border-gray-50! dark:border-gray-850!'}"
										style={token.align[cellIdx] ? `text-align: ${token.align[cellIdx]}` : ''}
									>
										<div class="break-normal">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-row-${rowIdx}-${cellIdx}`}
												tokens={normalizeTokens(cell.tokens ?? [])}
												{done}
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
		</div>
	{:else if token.type === 'blockquote'}
		{@const alert = alertComponent(token)}
		{#if alert}
			<AlertRenderer {token} {alert} />
		{:else}
			<blockquote dir="auto">
				<svelte:self
					id={`${id}-${tokenIdx}`}
					tokens={token.tokens}
					{done}
					{editCodeBlock}
					{onTaskClick}
					{onSourceClick}
				/>
			</blockquote>
		{/if}
	{:else if token.type === 'list'}
		{#if token.ordered}
			<ol start={token.start || 1} dir="auto">
				{#each token.items as item, itemIdx}
					<li class="text-start">
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
							{done}
							{editCodeBlock}
							{onTaskClick}
							{onSourceClick}
						/>
					</li>
				{/each}
			</ol>
		{:else}
			<ul dir="auto" class="">
				{#each token.items as item, itemIdx}
					<li class="text-start {item?.task ? 'flex -translate-x-6.5 gap-3 ' : ''}">
						{#if item?.task}
							<input
								class=""
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

							<div>
								<svelte:self
									id={`${id}-${tokenIdx}-${itemIdx}`}
									tokens={item.tokens}
									top={token.loose}
									{done}
									{editCodeBlock}
									{onTaskClick}
									{onSourceClick}
								/>
							</div>
						{:else}
							<svelte:self
								id={`${id}-${tokenIdx}-${itemIdx}`}
								tokens={item.tokens}
								top={token.loose}
								{done}
								{editCodeBlock}
								{onTaskClick}
								{onSourceClick}
							/>
						{/if}
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
					tokens={marked.lexer(decode(token.text))}
					attributes={token?.attributes}
					{done}
					{editCodeBlock}
					{onTaskClick}
					{onSourceClick}
				/>
			</div>
		</Collapsible>
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} {onSourceClick} />
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			on:load={(e) => {
				try {
					e.currentTarget.style.height =
						e.currentTarget.contentWindow.document.body.scrollHeight + 20 + 'px';
				} catch {}
			}}
		></iframe>
	{:else if token.type === 'paragraph'}
		<p dir="auto">
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{done}
				{onSourceClick}
			/>
		</p>
	{:else if token.type === 'text'}
		{#if top}
			<p>
				{#if token.tokens}
					<MarkdownInlineTokens
						id={`${id}-${tokenIdx}-t`}
						tokens={token.tokens}
						{done}
						{onSourceClick}
					/>
				{:else}
					{unescapeHtml(token.text)}
				{/if}
			</p>
		{:else if token.tokens}
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{done}
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
