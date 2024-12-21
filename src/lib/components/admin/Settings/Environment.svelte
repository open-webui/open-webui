<script>
  import { getEnvVariables } from '$lib/utils/env';
  import { onMount } from 'svelte';

  let envVariables = [];
  let error = null;

  onMount(async () => {
    try {
      envVariables = await getEnvVariables();
    } catch (e) {
      error = e.message;
    }
  });
</script>

<style>
  .env-list {
    list-style: none;
    padding: 0;
  }
  .env-item {
    padding: 8px;
    margin: 4px 0;
    background: #f5f5f5;
    border-radius: 4px;
  }
  .error {
    color: #dc3545;
    padding: 8px;
    margin: 8px 0;
    background: #f8d7da;
    border-radius: 4px;
  }
</style>

<div class="settings-section">
  <h2>Environment Settings</h2>
  
  {#if error}
    <div class="error">
      Error loading environment variables: {error}
    </div>
  {/if}

  {#if envVariables.length === 0}
    <p>No environment variables found.</p>
  {:else}
    <ul class="env-list">
      {#each envVariables as { key, value }}
        <li class="env-item">
          <strong>{key}:</strong> {value}
        </li>
      {/each}
    </ul>
  {/if}
</div>
