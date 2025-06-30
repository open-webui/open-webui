<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let selectedFile: File | null = null;
  let inputElement: HTMLInputElement;

  const handleFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      selectedFile = target.files[0];
    } else {
      selectedFile = null;
    }
  };

  const handleUploadClick = () => {
    if (selectedFile) {
      dispatch('upload', selectedFile);
    }
  };

  const openFileDialog = () => {
    inputElement?.click();
  }
</script>

<div class="flex flex-col items-center p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
  <input
    type="file"
    class="hidden"
    bind:this={inputElement}
    on:change={handleFileChange}
    accept="*"
  />
  <button
    on:click={openFileDialog}
    class="px-4 py-2 mb-2 text-white bg-blue-500 hover:bg-blue-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-300"
  >
    {#if selectedFile}
      {selectedFile.name} (Click to change)
    {:else}
      Select File
    {/if}
  </button>
  {#if selectedFile}
    <button
      on:click={handleUploadClick}
      class="px-4 py-2 text-white bg-green-500 hover:bg-green-600 rounded-md focus:outline-none focus:ring-2 focus:ring-green-300"
    >
      Upload
    </button>
  {/if}
</div>
