<script lang="ts">
	export let options: string[];
	export let selected: string;
	export let onSelect: (option: string) => void;
	export let isDark: boolean = false;
	export let size: 'sm' | 'md' | 'lg' = 'md';

	const sizeClasses = {
		sm: 'px-3 py-1 text-xs',
		md: 'px-4 py-1.5 text-sm',
		lg: 'px-5 py-2 text-base'
	};
</script>

<div
	class="inline-flex rounded-lg p-1 {isDark ? 'bg-gray-800' : 'bg-gray-100'}"
>
	{#each options as option}
		<button
			class="rounded-md font-medium transition-all {sizeClasses[size]} {selected.toLowerCase() ===
			option.toLowerCase()
				? 'bg-[#5CC9D3] text-white shadow-sm'
				: isDark
					? 'text-gray-400 hover:text-white'
					: 'text-gray-600 hover:text-gray-900'}"
			on:click={() => onSelect(option)}
		>
			{option}
		</button>
	{/each}
</div>
