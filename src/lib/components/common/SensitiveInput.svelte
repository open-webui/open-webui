<script lang="ts">
	interface Props {
		value?: string;
		placeholder?: string;
		required?: boolean;
		readOnly?: boolean;
		outerClassName?: string;
		inputClassName?: string;
		showButtonClassName?: string;
	}

	let {
		value = $bindable(''),
		placeholder = '',
		required = true,
		readOnly = false,
		outerClassName = 'flex flex-1 bg-transparent',
		inputClassName = 'w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-hidden',
		showButtonClassName = 'pl-1.5  transition bg-transparent'
	}: Props = $props();

	let show = $state(false);
</script>

<div class={outerClassName}>
	<input
		class={`${inputClassName} ${show ? '' : 'password'}`}
		autocomplete="off"
		disabled={readOnly}
		{placeholder}
		required={required && !readOnly}
		type="text"
		bind:value
	/>
	<button
		class={showButtonClassName}
		onclick={(e) => {
			e.preventDefault();
			show = !show;
		}}
		type="button"
	>
		{#if show}
			<svg
				class="size-4"
				fill="currentColor"
				viewBox="0 0 16 16"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					clip-rule="evenodd"
					d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5 10.5a.75.75 0 1 0 1.06-1.06l-1.322-1.323a7.012 7.012 0 0 0 2.16-3.11.87.87 0 0 0 0-.567A7.003 7.003 0 0 0 4.82 3.76l-1.54-1.54Zm3.196 3.195 1.135 1.136A1.502 1.502 0 0 1 9.45 8.389l1.136 1.135a3 3 0 0 0-4.109-4.109Z"
					fill-rule="evenodd"
				/>
				<path
					d="m7.812 10.994 1.816 1.816A7.003 7.003 0 0 1 1.38 8.28a.87.87 0 0 1 0-.566 6.985 6.985 0 0 1 1.113-2.039l2.513 2.513a3 3 0 0 0 2.806 2.806Z"
				/>
			</svg>
		{:else}
			<svg
				class="size-4"
				fill="currentColor"
				viewBox="0 0 16 16"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
				<path
					clip-rule="evenodd"
					d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
					fill-rule="evenodd"
				/>
			</svg>
		{/if}
	</button>
</div>
