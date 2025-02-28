<script lang="ts">
  import MarkdownInlineTokens from './MarkdownInlineTokens.svelte';
  import DOMPurify from 'dompurify';
  import { toast } from 'svelte-sonner';

  import type { Token } from 'marked';
  import { getContext } from 'svelte';

  const i18n = getContext('i18n');

  import { WEBUI_BASE_URL } from '$lib/constants';
  import { copyToClipboard, unescapeHtml } from '$lib/utils';

  import Image from '$lib/components/common/Image.svelte';
  import KatexRenderer from './KatexRenderer.svelte';
  import Source from './Source.svelte';
  import Iframe from '$lib/components/common/Iframe.svelte';

  interface Props {
    id: string;
    tokens: Token[];
    onSourceClick?: Function;
  }

  let { id, tokens, onSourceClick = () => {} }: Props = $props();
</script>

{#each tokens as token}
  {#if token.type === 'escape'}
    {unescapeHtml(token.text)}
  {:else if token.type === 'html'}
    {@const html = DOMPurify.sanitize(token.text)}
    {#if html && html.includes('<video')}
      {@html html}
    {:else if token.text.includes(`<iframe src="${WEBUI_BASE_URL}/api/v1/files/`)}
      {@html `${token.text}`}
    {:else if token.text.includes(`<source_id`)}
      <Source
        {id}
        onClick={onSourceClick}
        {token}
      />
    {:else}
      {token.text}
    {/if}
  {:else if token.type === 'link'}
    {#if token.tokens}
      <a
        href={token.href}
        rel="nofollow"
        target="_blank"
        title={token.title}
      >
        <MarkdownInlineTokens
          id={`${id}-a`}
          {onSourceClick}
          tokens={token.tokens}
        />
      </a>
    {:else}
      <a
        href={token.href}
        rel="nofollow"
        target="_blank"
        title={token.title}
      >{token.text}</a>
    {/if}
  {:else if token.type === 'image'}
    <Image
      alt={token.text}
      src={token.href}
    />
  {:else if token.type === 'strong'}
    <strong><MarkdownInlineTokens
      id={`${id}-strong`}
      {onSourceClick}
      tokens={token.tokens}
    /></strong>
  {:else if token.type === 'em'}
    <em><MarkdownInlineTokens
      id={`${id}-em`}
      {onSourceClick}
      tokens={token.tokens}
    /></em>
  {:else if token.type === 'codespan'}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <code
      class="codespan cursor-pointer"
      onclick={() => {
        copyToClipboard(unescapeHtml(token.text));
        toast.success($i18n.t('Copied to clipboard'));
      }}
    >{unescapeHtml(token.text)}</code>
  {:else if token.type === 'br'}
    <br />
  {:else if token.type === 'del'}
    <del><MarkdownInlineTokens
      id={`${id}-del`}
      {onSourceClick}
      tokens={token.tokens}
    /></del>
  {:else if token.type === 'inlineKatex'}
    {#if token.text}
      <KatexRenderer
        content={token.text}
        displayMode={false}
      />
    {/if}
  {:else if token.type === 'iframe'}
    <Iframe
      src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
      title={token.fileId}
    />
  {:else if token.type === 'text'}
    {token.raw}
  {/if}
{/each}
