<script lang="ts">
	const i18n = getContext('i18n');
	import { getContext } from 'svelte';
	import { settings } from '$lib/stores';
	export let id = 'password-input';
	export let value: string = '';
	export let placeholder = '';
	export let type = 'text';
	export let required = true;
	export let readOnly = false;
	export let outerClassName = 'flex flex-1 bg-transparent';
	export let inputClassName = 'w-full text-sm py-0.5 bg-transparent';
	export let showButtonClassName = 'pl-1.5  transition bg-transparent';

	let show = false;
</script>

<div class={outerClassName}>
	<label class="sr-only" for={id}>{placeholder || $i18n.t('Password')}</label>
	<input
		{id}
		class={`${inputClassName} ${show ? '' : 'password'} ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : ' outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-600'}`}
		{placeholder}
		type={type === 'password' && !show ? 'password' : 'text'}
		{value}
		required={required && !readOnly}
		disabled={readOnly}
		on:change={(e) => {
			value = e.target.value;
		}}
		autocomplete="off"
	/>
	<button
		class={showButtonClassName}
		type="button"
		aria-pressed={show}
		aria-label={$i18n.t('Make password visible in the user interface')}
		on:click={(e) => {
			e.preventDefault();
			show = !show;
		}}
	>
		{#if show}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				aria-hidden="true"
				class="size-4"
			>
				<path
					fill-rule="evenodd"
					d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5 10.5a.75.75 0 1 0 1.06-1.06l-1.322-1.323a7.012 7.012 0 0 0 2.16-3.11.87.87 0 0 0 0-.567A7.003 7.003 0 0 0 4.82 3.76l-1.54-1.54Zm3.196 3.195 1.135 1.136A1.502 1.502 0 0 1 9.45 8.389l1.136 1.135a3 3 0 0 0-4.109-4.109Z"
					clip-rule="evenodd"
				/>
				<path
					d="m7.812 10.994 1.816 1.816A7.003 7.003 0 0 1 1.38 8.28a.87.87 0 0 1 0-.566 6.985 6.985 0 0 1 1.113-2.039l2.513 2.513a3 3 0 0 0 2.806 2.806Z"
				/>
			</svg>
		{:else}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="size-4"
				aria-hidden="true"
			>
				<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
				<path
					fill-rule="evenodd"
					d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
					clip-rule="evenodd"
				/>
			</svg>
		{/if}
	</button>
</div>
