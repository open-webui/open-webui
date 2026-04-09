<script lang="ts">
  import { onMount } from 'svelte';

  const ENTITY_TYPES = [
    { key: 'PERSON',        label: 'Name / Person' },
    { key: 'ORGANIZATION',  label: 'Organization' },
    { key: 'EMAIL_ADDRESS', label: 'Email' },
    { key: 'IBAN_CODE',     label: 'IBAN' },
    { key: 'PHONE_NUMBER',  label: 'Phone Number' },
    { key: 'ID',            label: 'ID' },
  ];

  let entityToggles: Record<string, boolean> = {};

  onMount(() => {
    const saved = localStorage.getItem('garnet_entity_toggles');
    if (saved) {
      entityToggles = JSON.parse(saved);
    } else {
      ENTITY_TYPES.forEach(e => (entityToggles[e.key] = true));
      localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
    }
  });

  function onChange(key: string, value: string) {
    entityToggles[key] = value === 'on';
    localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
    entityToggles = { ...entityToggles };
  }
</script>

<div class="flex flex-col w-full">
  <div class="mb-4">
    <h3 class="text-sm font-semibold text-gray-200">Garnet — Entity Detection</h3>
    <p class="text-xs text-gray-400 mt-1">Choose which entity types get pseudonymized before reaching the model.</p>
  </div>

  <div class="w-full rounded-lg overflow-hidden border border-gray-700">
    <!-- header row -->
    <div class="grid grid-cols-2 bg-gray-700 px-4 py-2">
      <span class="text-xs font-semibold uppercase tracking-wider text-gray-300">Entity Type</span>
      <span class="text-xs font-semibold uppercase tracking-wider text-gray-300 text-right">Detection</span>
    </div>

    <!-- entity rows -->
    {#each ENTITY_TYPES as entity, i}
      <div class="grid grid-cols-2 items-center px-4 py-3
                  {i % 2 === 0 ? 'bg-gray-800' : 'bg-gray-850'}
                  border-b border-gray-700 last:border-0">
        <span class="text-sm text-white">{entity.label}</span>
        <div class="flex justify-end">
          <select
            value={entityToggles[entity.key] ? 'on' : 'off'}
            on:change={(e) => onChange(entity.key, e.currentTarget.value)}
            class="bg-gray-700 text-white text-sm rounded px-3 py-1
                   border border-gray-600 focus:outline-none focus:border-blue-500
                   cursor-pointer min-w-[80px]"
          >
            <option value="on">On</option>
            <option value="off">Off</option>
          </select>
        </div>
      </div>
    {/each}
  </div>
</div>
