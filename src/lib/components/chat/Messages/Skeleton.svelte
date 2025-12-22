<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let size = 'md';
</script>

<div class="flex flex-row items-center gap-3">
	<!-- Circular Rotation Progress Bar -->
	<div class="relative w-7 h-7">
		<svg class="w-7 h-7 animate-spin" viewBox="0 0 28 28" fill="none">
			<!-- Background track circle -->
			<circle
				cx="14"
				cy="14"
				r="12"
				stroke="currentColor"
				stroke-width="3"
				class="text-gray-200 dark:text-gray-700"
			/>
			<!-- Rotating progress arc -->
			<circle
				cx="14"
				cy="14"
				r="12"
				stroke="#076EF4"
				stroke-width="3"
				stroke-linecap="round"
				stroke-dasharray="75.4"
				stroke-dashoffset="56.5"
				class="origin-center"
			/>
		</svg>
	</div>

	<!-- Loading Text -->
	<span class="text-body-4 text-gray-950 dark:text-gray-50">
		{$i18n.t('Generating response...')}
	</span>
</div>
