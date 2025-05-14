<script>
	export let id;
	export let label;
	export let selected;
	export let onClick;
</script>

<button
	class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selected
		? 'bg-gray-800'
		: 'hover:bg-gray-800'}"
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
