<script lang="ts">
	import { getContext } from 'svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	const i18n: any = getContext('i18n');
	export let compact = false;
	export let value: Record<string, any> = {};
	const focusNew = (node: HTMLInputElement, empty: boolean) => {
		if (empty) node.focus();
	};
</script>

<div class="flex flex-col justify-center">
	<div class="min-w-0 flex-1">
		{#each Object.keys(value ?? {}) as key}
			<div
				class={compact
					? 'mb-1 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-start gap-3 py-1'
					: 'mb-1 grid grid-cols-[1fr_auto] items-center gap-y-0.5 py-0.5'}
			>
				<label class="min-w-0">
					{#if compact}<span class="block text-xs text-gray-400 dark:text-gray-600"
							>{$i18n.t('Parameter')}</span
						>{/if}
					<input
						type="text"
						class={compact
							? 'w-full min-w-0 bg-transparent py-1 text-[0.8125rem] text-gray-700 outline-none placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700'
							: 'min-w-0 w-full bg-transparent text-xs text-gray-400 dark:text-gray-600 outline-none'}
						aria-label={$i18n.t('Custom Parameter Name')}
						placeholder={compact ? $i18n.t('e.g. temperature') : $i18n.t('Custom Parameter Name')}
						required={compact}
						pattern={compact ? '.*\\S.*' : undefined}
						use:focusNew={compact && key === ''}
						title={key}
						value={key}
						on:change={(event) => {
							const name = event.currentTarget.value.trim();
							if (name && name !== key) {
								value[name] = value[key];
								delete value[key];
								value = { ...value };
							}
						}}
					/>
				</label>
				<label class={compact ? 'min-w-0' : 'order-last col-span-2'}>
					{#if compact}<span class="block text-xs text-gray-400 dark:text-gray-600"
							>{$i18n.t('Value')}</span
						>{/if}
					<input
						type="text"
						class={compact
							? 'w-full min-w-0 bg-transparent py-1 text-[0.8125rem] text-gray-700 outline-none placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700'
							: 'w-full min-w-0 bg-transparent text-[0.8125rem] text-gray-700 dark:text-gray-300 outline-none'}
						aria-label={$i18n.t('Custom Parameter Value')}
						placeholder={compact ? $i18n.t('e.g. 0.7') : $i18n.t('Custom Parameter Value')}
						value={typeof value[key] === 'object' ? JSON.stringify(value[key]) : value[key]}
						on:input={(event) => (value = { ...value, [key]: event.currentTarget.value })}
					/>
				</label>
				<button
					type="button"
					class={compact
						? 'mt-4 flex h-5 w-3 items-center justify-center rounded text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'
						: 'flex shrink-0 rounded-sm p-1 px-3 text-xs outline-hidden transition'}
					aria-label={`${$i18n.t('Remove')} ${key || $i18n.t('parameter')}`}
					on:click={() => {
						delete value[key];
						value = { ...value };
					}}
				>
					{#if compact}<XMark className="size-3" />{:else}{$i18n.t('Remove')}{/if}
				</button>
			</div>
		{/each}
	</div>
	<button
		type="button"
		class={compact
			? 'flex w-fit items-center gap-1.5 whitespace-nowrap py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 disabled:opacity-40'
			: 'mt-1 mb-5 flex w-full items-center justify-center gap-2 text-center'}
		aria-label={$i18n.t('Add Custom Parameter')}
		title={$i18n.t('Add Custom Parameter')}
		disabled={compact && Object.hasOwn(value ?? {}, '')}
		on:click={() => {
			value = value ?? {};
			let key = compact ? '' : 'custom_param_name';
			let index = 2;
			while (key in value) key = `custom_param_name_${index++}`;
			value = { ...value, [key]: '' };
		}}
	>
		<Plus className={compact ? 'size-3' : 'size-4'} /><span
			>{$i18n.t(compact ? 'Add parameter' : 'Add Custom Parameter')}</span
		>
	</button>
</div>
