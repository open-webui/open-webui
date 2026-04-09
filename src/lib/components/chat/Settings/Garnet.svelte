<script lang="ts">
	import { onMount } from 'svelte';

	const ENTITY_TYPES = [
		{ key: 'PERSON', label: 'Name / Person' },
		{ key: 'ORGANIZATION', label: 'Organization' },
		{ key: 'EMAIL_ADDRESS', label: 'Email' },
		{ key: 'IBAN_CODE', label: 'IBAN' },
		{ key: 'PHONE_NUMBER', label: 'Phone Number' },
		{ key: 'ID', label: 'ID' }
	];

	let entityToggles: Record<string, boolean> = {};

	onMount(() => {
		const saved = localStorage.getItem('garnet_entity_toggles');
		if (saved) {
			entityToggles = JSON.parse(saved);
		} else {
			ENTITY_TYPES.forEach((e) => (entityToggles[e.key] = true));
			localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		}
	});

	function onChange(key: string, value: string) {
		entityToggles[key] = value === 'on';
		localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		entityToggles = { ...entityToggles };
	}
</script>

<div class="flex flex-col gap-1 p-4">
	<p class="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
		Entity Detection
	</p>
	{#each ENTITY_TYPES as entity}
		<div class="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
			<span class="text-sm text-white">{entity.label}</span>
			<select
				value={entityToggles[entity.key] ? 'on' : 'off'}
				on:change={(e) => onChange(entity.key, e.currentTarget.value)}
				class="bg-gray-800 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none focus:border-blue-500"
			>
				<option value="on">On</option>
				<option value="off">Off</option>
			</select>
		</div>
	{/each}
</div>
