<script lang="ts">
  import MarkdownTokens from './MarkdownTokens.svelte';
  import DOMPurify from 'dompurify';
  import { createEventDispatcher, onMount, getContext } from 'svelte';
  const i18n = getContext('i18n');

  import fileSaver from 'file-saver';
  const { saveAs } = fileSaver;

  import { marked, type Token } from 'marked';
  import { unescapeHtml } from '$lib/utils';

  import { WEBUI_BASE_URL } from '$lib/constants';

  import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
  import MarkdownInlineTokens from '$lib/components/chat/Messages/Markdown/MarkdownInlineTokens.svelte';
  import KatexRenderer from './KatexRenderer.svelte';
  import Collapsible from '$lib/components/common/Collapsible.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
  import Iframe from '$lib/components/common/Iframe.svelte';

  const dispatch = createEventDispatcher();



  interface Props {
    id: string;
    tokens: Token[];
    top?: boolean;
    attributes?: any;
    save?: boolean;
    onTaskClick?: Function;
    onSourceClick?: Function;
  }

  let {
    id,
    tokens,
    top = true,
    attributes = {},
    save = false,
    onTaskClick = () => {},
    onSourceClick = () => {}
  }: Props = $props();

  const headerComponent = (depth: number) => {
    return 'h' + depth;
  };

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

<!-- {JSON.stringify(tokens)} -->
{#each tokens as token, tokenIdx (tokenIdx)}
  {#if token.type === 'hr'}
    <hr class=" border-gray-100 dark:border-gray-850" />
  {:else if token.type === 'heading'}
    <svelte:element
      this={headerComponent(token.depth)}
      dir="auto"
    >
      <MarkdownInlineTokens
        id={`${id}-${tokenIdx}-h`}
        {onSourceClick}
        tokens={token.tokens}
      />
    </svelte:element>
  {:else if token.type === 'code'}
    {#if token.raw.includes('```')}
      <CodeBlock
        id={`${id}-${tokenIdx}`}
        {attributes}
        code={token?.text ?? ''}
        lang={token?.lang ?? ''}
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
        {save}
        {token}
      />
    {:else}
      {token.text}
    {/if}
  {:else if token.type === 'table'}
    <div class="relative w-full group">
      <div class="scrollbar-hidden relative overflow-x-auto max-w-full rounded-lg">
        <table class=" w-full text-sm text-left text-gray-500 dark:text-gray-400 max-w-full rounded-xl">
          <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 border-none">
            <tr class="">
              {#each token.header as header, headerIdx}
                <th
                  style={token.align[headerIdx] ? '' : `text-align: ${token.align[headerIdx]}`}
                  class="px-3! py-1.5! cursor-pointer border border-gray-100 dark:border-gray-850"
                  scope="col"
                >
                  <div class="flex flex-col gap-1.5 text-left">
                    <div class="shrink-0 break-normal">
                      <MarkdownInlineTokens
                        id={`${id}-${tokenIdx}-header-${headerIdx}`}
                        {onSourceClick}
                        tokens={header.tokens}
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
                    style={token.align[cellIdx] ? '' : `text-align: ${token.align[cellIdx]}`}
                    class="px-3! py-1.5! text-gray-900 dark:text-white w-max border border-gray-100 dark:border-gray-850"
                  >
                    <div class="flex flex-col break-normal">
                      <MarkdownInlineTokens
                        id={`${id}-${tokenIdx}-row-${rowIdx}-${cellIdx}`}
                        {onSourceClick}
                        tokens={cell.tokens}
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
            onclick={(e) => {
              e.stopPropagation();
              exportTableToCSVHandler(token, tokenIdx);
            }}
          >
            <ArrowDownTray
              className=" size-3.5"
              strokeWidth="1.5"
            />
          </button>
        </Tooltip>
      </div>
    </div>
  {:else if token.type === 'blockquote'}
    <blockquote dir="auto">
      <MarkdownTokens
        id={`${id}-${tokenIdx}`}
        {onSourceClick}
        {onTaskClick}
        tokens={token.tokens}
      />
    </blockquote>
  {:else if token.type === 'list'}
    {#if token.ordered}
      <ol start={token.start || 1}>
        {#each token.items as item, itemIdx}
          <li
            class="text-start"
            dir="auto"
          >
            {#if item?.task}
              <input
                class=" translate-y-[1px] -translate-x-1"
                checked={item.checked}
                type="checkbox"
                onchange={(e) => {
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

            <MarkdownTokens
              id={`${id}-${tokenIdx}-${itemIdx}`}
              {onSourceClick}
              {onTaskClick}
              tokens={item.tokens}
              top={token.loose}
            />
          </li>
        {/each}
      </ol>
    {:else}
      <ul>
        {#each token.items as item, itemIdx}
          <li
            class="text-start"
            dir="auto"
          >
            {#if item?.task}
              <input
                class=" translate-y-[1px] -translate-x-1"
                checked={item.checked}
                type="checkbox"
                onchange={(e) => {
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

            <MarkdownTokens
              id={`${id}-${tokenIdx}-${itemIdx}`}
              {onSourceClick}
              {onTaskClick}
              tokens={item.tokens}
              top={token.loose}
            />
          </li>
        {/each}
      </ul>
    {/if}
  {:else if token.type === 'details'}
    <Collapsible
      attributes={token?.attributes}
      className="w-full space-y-1"
      dir="auto"
      title={token.summary}
    >
      {#snippet content()}
                                    <div
          
          class=" mb-1.5"
        >
          <MarkdownTokens
            id={`${id}-${tokenIdx}-d`}
            attributes={token?.attributes}
            {onSourceClick}
            {onTaskClick}
            tokens={marked.lexer(token.text)}
          />
        </div>
                                  {/snippet}
    </Collapsible>
  {:else if token.type === 'html'}
    {@const html = DOMPurify.sanitize(token.text)}
    {#if html && html.includes('<video')}
      {@html html}
    {:else if token.text.includes(`<iframe src="${WEBUI_BASE_URL}/api/v1/files/`)}
      {@html `${token.text}`}
    {:else}
      {token.text}
    {/if}
  {:else if token.type === 'iframe'}
    <Iframe
      src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
      title={token.fileId}
    />
  {:else if token.type === 'paragraph'}
    <p dir="auto">
      <MarkdownInlineTokens
        id={`${id}-${tokenIdx}-p`}
        {onSourceClick}
        tokens={token.tokens ?? []}
      />
    </p>
  {:else if token.type === 'text'}
    {#if top}
      <p dir="auto">
        {#if token.tokens}
          <MarkdownInlineTokens
            id={`${id}-${tokenIdx}-t`}
            {onSourceClick}
            tokens={token.tokens}
          />
        {:else}
          {unescapeHtml(token.text)}
        {/if}
      </p>
    {:else if token.tokens}
      <MarkdownInlineTokens
        id={`${id}-${tokenIdx}-p`}
        {onSourceClick}
        tokens={token.tokens ?? []}
      />
    {:else}
      {unescapeHtml(token.text)}
    {/if}
  {:else if token.type === 'inlineKatex'}
    {#if token.text}
      <KatexRenderer
        content={token.text}
        displayMode={token?.displayMode ?? false}
      />
    {/if}
  {:else if token.type === 'blockKatex'}
    {#if token.text}
      <KatexRenderer
        content={token.text}
        displayMode={token?.displayMode ?? false}
      />
    {/if}
  {:else if token.type === 'space'}
    <div class="my-2"></div>
  {:else}
    {console.log('Unknown token', token)}
  {/if}
{/each}
