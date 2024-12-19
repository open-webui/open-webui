<script>
  import { slide } from 'svelte/transition';
  
  export let thought = '';
  export let output = '';
  
  let showThought = false;
</script>

<div class="thought-output-container">
  <div class="flex items-center gap-2 mb-2">
    <button
      class="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      on:click={() => showThought = !showThought}
    >
      <svg
        class="w-4 h-4 transition-transform duration-200"
        style="transform: rotate({showThought ? '90deg' : '0deg'})"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path d="M6.293 7.293a1 1 0 011.414 0L10 9.586l2.293-2.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" />
      </svg>
      {showThought ? 'Hide thought process' : 'Show thought process'}
    </button>
  </div>

  {#if showThought}
    <div 
      class="pl-4 mb-4 border-l-2 border-gray-200 dark:border-gray-700"
      transition:slide
    >
      <div class="text-sm text-gray-600 dark:text-gray-300">
        <slot name="thought">
          {@html thought}
        </slot>
      </div>
    </div>
  {/if}

  <div class="output">
    <slot name="output">
      {@html output}
    </slot>
  </div>
</div> 