<script>
  // Assuming you have a way to get environment variables
  import { getEnvVariables } from '$lib/utils/env';
  import { onMount } from 'svelte';

  let envVariables = [];

  onMount(async () => {
    envVariables = await getEnvVariables();
  });
</script>

<style>
  /* Your existing styles */
</style>

<div class="settings-section">
  <h2>Environment Settings</h2>
  <ul>
    {#each envVariables as { key, value }}
      <li><strong>{key}:</strong> {value}</li>
    {/each}
  </ul>
</div>
