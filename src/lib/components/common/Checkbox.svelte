<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	export let checked = 'unchecked';
	export let indeterminate = false;

	let _checked = 'unchecked';

	$: _checked = checked;
</script>

<button
	class="-outline-offset-1 outline-[1.5px] outline-gray-200 dark:outline-gray-600 {checked !==
	'unchecked'
		? 'bg-black outline-black '
		: 'hover:outline-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'} text-white transition-all rounded-sm inline-block w-3.5 h-3.5 relative"
	type="button"
	on:click={() => {
		if (_checked === 'unchecked') {
			_checked = 'checked';
			dispatch('change', _checked);
		} else if (_checked === 'checked') {
			_checked = 'unchecked';
			if (!indeterminate) {
				dispatch('change', _checked);
			}
		} else if (indeterminate) {
			_checked = 'checked';
			dispatch('change', _checked);
		}
	}}
>
	<div class="top-0 left-0 absolute w-full flex justify-center">
		{#if _checked === 'checked'}
			<svg
				class="w-3.5 h-3.5"
				aria-hidden="true"
				fill="none"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					d="m5 12 4.7 4.5 9.3-9"
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
				/>
			</svg>
		{:else if indeterminate}
			<svg
				class="w-3 h-3.5 text-gray-800 dark:text-white"
				aria-hidden="true"
				fill="none"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					d="M5 12h14"
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
				/>
			</svg>
		{/if}
	</div>

	<!-- {checked} -->
</button>
