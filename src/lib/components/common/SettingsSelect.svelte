<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let value: string | number | boolean = '';
	export let id = '';
	export let name = '';
	export let ariaLabel = '';
	export let placeholder = '';
	export let required = false;
	export let disabled = false;
	export let className = 'w-fit max-w-full';
	export let selectClassName = '';
</script>

<div class="relative inline-flex {className}">
	<select
		{...$$restProps}
		bind:value
		id={id || undefined}
		name={name || undefined}
		aria-label={ariaLabel || undefined}
		title={placeholder || undefined}
		{required}
		{disabled}
		class="h-7 w-full max-w-full appearance-none truncate rounded-lg border border-gray-100/50 !bg-gray-50/40 ps-2.5 pe-8 text-left text-xs text-gray-700 outline-hidden transition-colors [field-sizing:content] focus:border-blue-400 disabled:opacity-50 dark:border-white/[0.04] dark:!bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500 {selectClassName}"
		on:change
	>
		<slot />
	</select>
	<ChevronDown
		className="pointer-events-none absolute end-2 top-1/2 size-3.5 -translate-y-1/2 text-gray-400 dark:text-gray-500"
		strokeWidth="2"
	/>
</div>
