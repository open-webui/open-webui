<script lang="ts">  
    import { onMount } from 'svelte';
    import SuccessIcon from '../icons/SuccessIcon.svelte';
    import ErrorIcon from '../icons/ErrorIcon.svelte';

    export let message: string;
    export let type: 'success' | 'error' = 'success';
    export let visible = false;
    export let duration = 3000;
  
    onMount(() => {
      if (visible && duration) {
        setTimeout(() => {
          visible = false;
        }, duration);
      }
    });
  </script>
  
  {#if visible}
    <div
      class="w-full md:w-[31rem] fixed top-2 left-1/2 transform -translate-x-1/2 bg-white dark:bg-customGray-800 shadow-lg rounded-lg px-8 md:px-12 py-3 md:py-5 flex flex-col items-center gap-3 z-50"
    >
      {#if type === 'success'}
        <SuccessIcon  />
      {:else if type === 'error'}
        <ErrorIcon />
      {/if}
  
      <div class="text-sm text-lightGray-100 dark:text-white text-center">
        {message}
      </div>
    </div>
  {/if}
  
 