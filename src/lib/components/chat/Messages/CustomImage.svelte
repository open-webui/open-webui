<script lang="ts">
 export let data: any;
  let parsed: any;

  $: {
    if (typeof data === 'string') {
      try {
        parsed = JSON.parse(data);
      } catch {
        parsed = {};
      }
    } else {
      parsed = data;
    }
  }
</script>

{#if parsed?.src || parsed?.url}
  <img
    src={parsed.src ?? parsed.url}
    alt={parsed.alt ?? 'Image'}
    style="max-width: 100%; border-radius: 8px;"
    loading="lazy"
  />
{:else}
  <span class="text-red-500 text-xs">[Image non disponible]</span>
{/if}
