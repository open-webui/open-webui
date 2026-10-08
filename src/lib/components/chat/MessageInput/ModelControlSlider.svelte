<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { ModelControl } from '$lib/apis';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher<{ change: string }>();
	export let control: ModelControl;
	export let value = '';
	export let disabled = false;
	let editing = false;
	$: options = Object.entries(control.options);
	$: index = Math.max(
		0,
		options.findIndex(([key]) => key === (value || control.default))
	);
	$: progress = (index / Math.max(1, options.length - 1)) * 100;
	$: current = editing ? options[index]?.[0] : value || control.default;
	$: label = control.options[current ?? '']?.label ?? $i18n.t('Default');
</script>

<div class="space-y-2 px-2 py-2 text-xs">
	<div class="flex items-center gap-2">
		<span class="text-gray-700 dark:text-gray-100">{control.label}</span>
		<span class="min-w-0 flex-1 truncate text-gray-500 dark:text-gray-400">{label}</span>
		{#if control.description}
			<Tooltip content={control.description}>
				<button
					type="button"
					aria-label={control.description}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				>
					<QuestionMarkCircle className="size-3.5" />
				</button>
			</Tooltip>
		{/if}
	</div>
	<div class="space-y-1">
		<div
			class="flex justify-between gap-2 text-[0.6875rem] text-gray-500 dark:text-gray-400"
			aria-hidden="true"
		>
			<span class="truncate">{options[0]?.[1].label}</span>
			<span class="truncate text-right">{options.at(-1)?.[1].label}</span>
		</div>
		<div class="relative flex h-5 items-center">
			<div class="pointer-events-none absolute inset-x-2.5 flex justify-between" aria-hidden="true">
				{#each options as [key] (key)}
					<span class="size-0.5 rounded-full bg-gray-400 dark:bg-gray-500"></span>
				{/each}
			</div>
			<input
				type="range"
				min="0"
				max={options.length - 1}
				step="1"
				bind:value={index}
				{disabled}
				aria-label={control.label}
				aria-valuetext={label}
				class="control-slider h-5 w-full cursor-pointer appearance-none rounded-md bg-gray-100 outline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-400 disabled:cursor-wait [--slider-fill:var(--color-gray-300)] dark:bg-gray-800 dark:[--slider-fill:var(--color-gray-600)]"
				style:background-image={`linear-gradient(to right, var(--slider-fill) ${progress}%, transparent ${progress}%)`}
				on:input={() => (editing = true)}
				on:change={() => {
					dispatch('change', options[index][0]);
					editing = false;
				}}
				on:pointerup={() => {
					if (!current) dispatch('change', options[index][0]);
				}}
			/>
		</div>
	</div>
	<button
		type="button"
		disabled={disabled || !value}
		on:click={() => dispatch('change', '')}
		class="text-[0.6875rem] text-gray-500 transition enabled:hover:text-gray-900 dark:text-gray-400 dark:enabled:hover:text-gray-100"
	>
		{$i18n.t('Default')}{#if control.options[control.default ?? '']?.label}{' · '}{control.options[
				control.default ?? ''
			].label}{/if}
	</button>
</div>

<style>
	.control-slider::-webkit-slider-thumb {
		appearance: none;
		width: 1rem;
		height: 1.25rem;
		border-radius: 0.375rem;
		background: white;
		box-shadow: 0 1px 3px #0003;
	}
	.control-slider::-moz-range-thumb {
		width: 1rem;
		height: 1.25rem;
		border: 0;
		border-radius: 0.375rem;
		background: white;
		box-shadow: 0 1px 3px #0003;
	}
</style>
