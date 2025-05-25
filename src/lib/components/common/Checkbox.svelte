<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import CheckmarkIcon from '../icons/CheckmarkIcon.svelte';
	const dispatch = createEventDispatcher();

	export let state = 'unchecked';
	export let indeterminate = false;

	let _state = 'unchecked';

	$: _state = state;
</script>

<button
	class=" outline -outline-offset-1 outline-[1.5px] outline-lightGray-1000 dark:outline-gray-600 {state !==
	'unchecked'
		? 'bg-white dark:bg-customGray-900 outline-black '
		: 'hover:outline-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'} text-lightGray-100 dark:text-white transition-all rounded inline-block w-3.5 h-3.5 relative"
	on:click={() => {
		if (_state === 'unchecked') {
			_state = 'checked';
			dispatch('change', _state);
		} else if (_state === 'checked') {
			_state = 'unchecked';
			if (!indeterminate) {
				dispatch('change', _state);
			}
		} else if (indeterminate) {
			_state = 'checked';
			dispatch('change', _state);
		}
	}}
	type="button"
>
	<div class="top-0 left-0 absolute w-full flex justify-center">
		{#if _state === 'checked'}
			<CheckmarkIcon className="size-3.5"/>
		{:else if indeterminate}
			<svg
				class="w-3 h-3.5 text-gray-800 dark:text-white"
				aria-hidden="true"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
			>
				<path
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
					d="M5 12h14"
				/>
			</svg>
		{/if}
	</div>

	<!-- {checked} -->
</button>
