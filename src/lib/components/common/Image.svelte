<script lang="ts">
  import { run } from 'svelte/legacy';

  import { WEBUI_BASE_URL } from '$lib/constants';
  import ImagePreview from './ImagePreview.svelte';


  interface Props {
    src?: string;
    alt?: string;
    className?: string;
    imageClassName?: string;
  }

  let {
    src = '',
    alt = '',
    className = ' w-full outline-hidden focus:outline-hidden',
    imageClassName = 'rounded-lg'
  }: Props = $props();

  let _src = $state('');
  run(() => {
    _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;
  });

  let showImagePreview = $state(false);
</script>

<button
  class={className}
  type="button"
  onclick={() => {
    showImagePreview = true;
  }}
>
  <img
    class={imageClassName}
    {alt}
    data-cy="image"
    draggable="false"
    src={_src}
  />
</button>

<ImagePreview
  {alt}
  src={_src}
  bind:show={showImagePreview}
/>
