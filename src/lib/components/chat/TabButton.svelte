<script>
	export let id;
	export let label;
	export let selected;
	export let onClick;
</script>

<button
	class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selected
		? ''
		: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
	on:click={onClick}
	role="tab"
	aria-selected={selected}
	aria-controls={`${id}-content`}
	aria-label={label}
>
	<div class=" self-center mr-2">
		<slot></slot>
	</div>
	<div class="self-center">{label}</div>
</button>
