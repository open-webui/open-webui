<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  export let x;
  export let y;

  let popupElement = null;

  onMount(() => {
    document.body.appendChild(popupElement);
    document.body.style.overflow = 'hidden';
  });

  onDestroy(() => {
    document.body.removeChild(popupElement);
    document.body.style.overflow = 'unset';
  });
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->

<div
  bind:this={popupElement}
  class="fixed top-0 left-0 w-screen h-[100dvh] z-50 touch-none pointer-events-none"
>
  <div
    style:top="{y + 10}px"
    style:left="{x + 10}px"
    class=" absolute text-white z-99999"
  >
    <slot />
  </div>
</div>
