<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import { settings } from '$lib/stores';
	export let statusMessages: Record<string, string | null> = {};
	export let expanded = false;
	const DEFAULT_EXECUTING = "Executing tool call...";
	const DEFAULT_COMPLETED = "Completed tool call";
	$: isOff = (statusMessages["executing"] ?? null) === null && (statusMessages["completed"] ?? null) === null;
	const toggleMain = () => {
		if (expanded) {
			statusMessages["executing"] = null;
			statusMessages["completed"] = null;
		} else {
			statusMessages["executing"] = DEFAULT_EXECUTING;
			statusMessages["completed"] = DEFAULT_COMPLETED;
		}
		expanded = !expanded;
	};
	const toggleExecuting = () => {
		if (statusMessages["executing"] === DEFAULT_EXECUTING) {
			statusMessages["executing"] = null;
		} else {
			statusMessages["executing"] = DEFAULT_EXECUTING;
		}
	};
	const toggleCompleted = () => {
		if (statusMessages["completed"] === DEFAULT_COMPLETED) {
			statusMessages["completed"] = null;
		} else {
			statusMessages["completed"] = DEFAULT_COMPLETED;
		}
	};
	$: executingButtonText = statusMessages["executing"] === DEFAULT_EXECUTING ? 'Default' : 'Custom';
	$: completedButtonText = statusMessages["completed"] === DEFAULT_COMPLETED ? 'Default' : 'Custom';
</script>

<div class="flex flex-col w-full mt-2">
	<div class="flex w-full justify-between">
		<div class={`mb-1 text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100 placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 text-gray-500'}`}>
			{$i18n.t('Status Messages')}
		</div>
		<button
			class="p-1 px-3 text-xs flex rounded-sm transition cursor-pointer"
			type="button"
			on:click={toggleMain}
			on:mousedown={toggleMain}
		>
			{#if isOff}
				{$i18n.t('Off')}
			{:else}
				{$i18n.t('On')}
			{/if}
		</button>
	</div>

	{#if !isOff}
		<div class="flex flex-col mt-2 space-y-3">
			<!-- Executing Status Message -->
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between mb-1">
					<div class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}>
						Executing status
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						type="button"
						on:click={toggleExecuting}
					>
						<span class="ml-2 self-center">{$i18n.t(executingButtonText)}</span>
					</button>
				</div>
				<div class="flex-1">
					<input
						class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
						type="text"
						bind:value={statusMessages["executing"]}
						placeholder={$i18n.t('Status to be shown while the tool is executing')}
						autocomplete="off"
					/>
				</div>
			</div>

			<!-- Completed Status Message -->
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between mb-1">
					<div class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}>
						Completed status
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						type="button"
						on:click={toggleCompleted}
					>
						<span class="ml-2 self-center">{$i18n.t(completedButtonText)}</span>
					</button>
				</div>
				<div class="flex-1">
					<input
						class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
						type="text"
						bind:value={statusMessages["completed"]}
						placeholder={$i18n.t('Status to be shown when the tool call is completed')}
						autocomplete="off"
					/>
				</div>
			</div>
		</div>
	{/if}
</div>
