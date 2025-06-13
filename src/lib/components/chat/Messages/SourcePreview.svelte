<script lang="ts">
  export let source;

  let showModal = false;
</script>

<span
  class="cursor-pointer text-blue-600 underline"
  on:click={() => (showModal = true)}
>
  🔍 {source.filename}{source.page ? ` (page ${source.page})` : ''}
</span>

{#if showModal}
  <div class="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-900 p-6 rounded-xl min-w-[300px] max-w-[90vw] relative shadow-2xl">
      <button
        class="absolute top-2 right-2 text-gray-500 hover:text-red-500 text-2xl"
        on:click={() => (showModal = false)}
        aria-label="Close"
      >
        ✖️
      </button>
      <h2 class="font-bold mb-2">
        {source.filename}{source.page ? ` - page ${source.page}` : ''}
      </h2>
      <div>
        {#if source.page_content}
          <pre class="text-xs whitespace-pre-wrap bg-gray-100 dark:bg-gray-800 rounded p-2">{source.page_content}</pre>
        {:else}
          <em class="text-gray-500">Aucun contenu extrait.</em>
        {/if}
      </div>
    </div>
  </div>
{/if}
