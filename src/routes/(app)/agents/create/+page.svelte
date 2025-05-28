<script lang="ts">
  import AgentCreationForm from '$lib/components/agents/AgentCreationForm.svelte';
</script>

<div class="container mx-auto p-4">
  <h1 class="text-2xl font-bold mb-4">Create New Agent</h1>
  <AgentCreationForm />
</div>

<style>
  .container {
    max-width: 800px;
  }
</style>
