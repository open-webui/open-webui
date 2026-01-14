<script lang="ts">
	export let chips: { id: string; label: string }[];
	export let selected: string;
	export let onSelect: (id: string) => void;
	export let isDark: boolean = false;
</script>

<div class="flex flex-wrap gap-2">
	{#each chips as chip}
		<button
			class="px-4 py-2 rounded-full text-sm font-medium transition-all {selected === chip.id
				? 'bg-[#5CC9D3] text-white'
				: isDark
					? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
					: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			on:click={() => onSelect(chip.id)}
		>
			{chip.label}
		</button>
	{/each}
</div>
