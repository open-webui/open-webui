<script lang="ts">
	import { onMount } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let onSelect: (prompt: string) => void = () => {};

	interface PresetAction {
		id: string;
		icon: string;
		label: string;
		prompt: string;
	}

	let presets: PresetAction[] = [];

	onMount(async () => {
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/presets`);
			if (res.ok) {
				presets = await res.json();
			}
		} catch {
			// Fallback presets if API unavailable
			presets = [
				{ id: 'triage', icon: '\u{1F4E7}', label: 'Triage emails', prompt: 'Revisa mis emails no leidos y ordenalos por urgencia' },
				{ id: 'summarize', icon: '\u{1F4C4}', label: 'Resumir docs', prompt: 'Resume el ultimo documento que subi' },
				{ id: 'draft', icon: '\u{270F}\u{FE0F}', label: 'Borrador', prompt: 'Prepara un borrador de respuesta profesional para...' },
				{ id: 'calendar', icon: '\u{1F4C5}', label: 'Agenda', prompt: 'Que tengo en mi calendario hoy?' },
				{ id: 'search', icon: '\u{1F50D}', label: 'Buscar', prompt: 'Busca en la web informacion sobre...' }
			];
		}
	});
</script>

{#if presets.length > 0}
	<div class="flex gap-2 overflow-x-auto scrollbar-hidden pb-1 px-1">
		{#each presets as preset}
			<button
				class="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 text-sm text-gray-700 dark:text-gray-300 transition whitespace-nowrap"
				on:click={() => onSelect(preset.prompt)}
			>
				<span>{preset.icon}</span>
				<span>{preset.label}</span>
			</button>
		{/each}
	</div>
{/if}
