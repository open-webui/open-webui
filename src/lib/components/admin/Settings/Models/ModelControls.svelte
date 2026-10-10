<script lang="ts">
	import ModelSettingsLabel from '$lib/components/workspace/Models/ModelSettingsLabel.svelte';
	import { getContext, tick } from 'svelte';
	// @ts-expect-error The existing SortableJS dependency does not ship declarations.
	import Sortable from 'sortablejs';
	import type { ModelControl } from '$lib/apis';
	import CustomParams from '$lib/components/chat/Settings/Advanced/CustomParams.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import NativeSelect from '$lib/components/common/NativeSelect.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';

	const i18n: any = getContext('i18n');
	export let controls: Record<string, ModelControl> = {};
	let show = false;
	let editingKey = '';
	let label = '';
	let description = '';
	let display: 'menu' | 'slider' = 'menu';
	let defaultOption = '';
	let options: { id: string; key?: string; label: string; params: Record<string, any> }[] = [];
	let nameInput: HTMLInputElement;
	const actionClass =
		'flex size-7 shrink-0 items-center justify-center rounded-lg text-gray-500 transition hover:bg-black/5 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-gray-200';
	const inputClass =
		'w-full min-w-0 bg-transparent py-1 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 font-normal text-gray-900 dark:text-gray-100';

	const keyFor = (label: string, items: object) => {
		let base = label
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, '_')
			.replace(/^_|_$/g, '');
		if (!/^[a-z]/.test(base) || ['constructor', 'prototype'].includes(base))
			base = `option_${base}`;
		let key = base;
		let index = 2;
		while (key in items) key = `${base}_${index++}`;
		return key;
	};
	const focus = (node: HTMLInputElement) => node.focus();
	const addOption = () => {
		options = [...options, { id: crypto.randomUUID(), label: '', params: { '': '' } }];
	};
	const edit = async (key = '') => {
		editingKey = key;
		const control = controls?.[key];
		label = control?.label ?? '';
		description = control?.description ?? '';
		display = control?.display ?? 'menu';
		defaultOption = control?.default ?? '';
		options = Object.entries(control?.options ?? {}).map(([key, option]) => ({
			id: key,
			key,
			label: option.label,
			params: structuredClone(option.params ?? {})
		}));
		if (!options.length) addOption();
		show = true;
		await tick();
		nameInput?.focus();
	};
	const apply = () => {
		const saved: ModelControl['options'] = {};
		// Reserve existing keys so a new option cannot overwrite a renamed option.
		const keys = Object.fromEntries(
			options.filter((option) => option.key).map((option) => [option.key!, true])
		);
		let selected: string | null = null;
		for (const option of options) {
			const key = option.key ?? keyFor(option.label, keys);
			keys[key] = true;
			saved[key] = { label: option.label.trim(), params: option.params };
			if (option.id === defaultOption) selected = key;
		}
		controls = {
			...controls,
			[editingKey || keyFor(label, controls ?? {})]: {
				label: label.trim(),
				...(display === 'slider' ? { display } : {}),
				...(description.trim() ? { description: description.trim() } : {}),
				default: selected,
				options: saved
			}
		};
		show = false;
	};
	const move = <T,>(items: T[], from: number, to: number): T[] => {
		if (to < 0 || to >= items.length) return items;
		const result = [...items];
		result.splice(to, 0, result.splice(from, 1)[0]);
		return result;
	};
	const moveControl = (from: number, to: number) => {
		controls = Object.fromEntries(move(Object.entries(controls ?? {}), from, to));
	};
	const moveOption = (from: number, to: number) => {
		options = move(options, from, to);
	};
	const keyboardMove = (
		event: KeyboardEvent,
		index: number,
		reorder: (from: number, to: number) => void
	) => {
		if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
		event.preventDefault();
		reorder(index, index + (event.key === 'ArrowUp' ? -1 : 1));
	};
	const sortable = (node: HTMLElement, reorder: (from: number, to: number) => void) => {
		let nextSibling: ChildNode | null;
		const instance = new Sortable(node, {
			animation: 150,
			handle: '.sort-handle',
			onStart: ({ item }: { item: HTMLElement }) => (nextSibling = item.nextSibling),
			onEnd: ({
				item,
				from,
				oldIndex,
				newIndex
			}: {
				item: HTMLElement;
				from: HTMLElement;
				oldIndex: number;
				newIndex: number;
			}) => {
				// Let Svelte reconcile the keyed rows in their original DOM order.
				from.insertBefore(item, nextSibling);
				reorder(oldIndex, newIndex);
			}
		});
		return { destroy: () => instance.destroy() };
	};
</script>

<div>
	<div
		class="grid grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 px-1 py-1.5 text-xs sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
	>
		<span class="text-xs font-normal text-gray-600 dark:text-gray-400"
			><ModelSettingsLabel
				label={$i18n.t('Model controls')}
				description={$i18n.t('Let people choose approved parameter presets in chat.')}
			/></span
		>
		<p
			class="truncate text-gray-500 dark:text-gray-400"
			title={$i18n.t('Let people choose approved parameter presets in chat.')}
		>
			{$i18n.t('Let people choose approved parameter presets in chat.')}
		</p>
		<button
			type="button"
			class="text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			aria-label={$i18n.t('Add control')}
			title={$i18n.t('Add control')}
			on:click={() => edit()}><Plus className="size-3" /></button
		>
	</div>
	<div use:sortable={moveControl}>
		{#each Object.entries(controls ?? {}) as [key, control], index (key)}
			<div class="flex items-center gap-1 py-0.5">
				<button
					type="button"
					class={`${actionClass} sort-handle cursor-grab`}
					aria-label={`${$i18n.t('Reorder')} ${control.label}`}
					title={$i18n.t('Drag or use the up and down arrow keys to reorder')}
					on:keydown={(event) => keyboardMove(event, index, moveControl)}
					><EllipsisVertical className="size-4" /></button
				>
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center justify-between gap-3 py-1 text-left text-[0.8125rem] font-normal text-gray-900 dark:text-gray-100"
					aria-label={`${$i18n.t('Edit')} ${control.label}`}
					on:click={() => edit(key)}
				>
					<span class="truncate">{control.label}</span>
					<span class="flex min-w-0 items-center gap-3 text-xs">
						<span class="truncate text-gray-400 dark:text-gray-600"
							>{$i18n.t('Default option')}: {control.options[control.default ?? '']?.label ??
								$i18n.t('None')}</span
						>
						<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Edit')}</span>
					</span>
				</button>
				<button
					type="button"
					class="ml-2 flex shrink-0 items-center justify-center rounded text-gray-400 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
					aria-label={`${$i18n.t('Remove')} ${control.label}`}
					on:click={() => {
						delete controls[key];
						controls = { ...controls };
					}}><XMark className="size-3" /></button
				>
			</div>
		{/each}
	</div>
</div>

<Modal size="sm" bind:show>
	<div class="px-5 pb-5 pt-4 dark:text-gray-200">
		<div class="mb-3 flex items-center justify-between gap-3">
			<div class="font-primary text-lg font-medium">
				{editingKey ? $i18n.t('Edit control') : $i18n.t('Add control')}
			</div>
			<button
				type="button"
				class={actionClass}
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}><XMark className="size-5" /></button
			>
		</div>
		<form class="space-y-2.5" on:submit|preventDefault|stopPropagation={apply}>
			<div class="grid grid-cols-[minmax(0,1fr)_minmax(0,8rem)] gap-4">
				<label class="block min-w-0 text-xs leading-4">
					<span class="text-xs font-normal text-gray-600 dark:text-gray-400">{$i18n.t('Name')}</span
					>
					<input
						bind:this={nameInput}
						class={inputClass}
						aria-label={$i18n.t('Control name')}
						placeholder={$i18n.t('e.g. Thinking')}
						bind:value={label}
						required
					/>
				</label>
				<label class="block min-w-0 text-xs leading-4">
					<span class="text-xs font-normal text-gray-600 dark:text-gray-400"
						>{$i18n.t('Default option')}</span
					>
					<NativeSelect
						value={defaultOption}
						options={[
							{ value: '', label: $i18n.t('None') },
							...options
								.filter((option) => option.label.trim())
								.map((option) => ({ value: option.id, label: option.label }))
						]}
						className={`${inputClass} block`}
						on:change={(event) => (defaultOption = event.detail)}
					/>
				</label>
			</div>
			<label class="block text-xs leading-4">
				<span class="text-xs font-normal text-gray-600 dark:text-gray-400"
					>{$i18n.t('Description')}</span
				>
				<input class={inputClass} placeholder={$i18n.t('Optional')} bind:value={description} />
			</label>
			<div class="flex items-center justify-between">
				<span class="text-xs font-normal text-gray-600 dark:text-gray-400"
					>{$i18n.t('Display')}</span
				>
				<div class="flex gap-1">
					{#each ['menu', 'slider'] as mode}
						<button
							type="button"
							aria-pressed={display === mode}
							class="rounded-lg px-2 py-1 text-xs transition {display === mode
								? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-white'
								: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
							on:click={() => (display = mode as 'menu' | 'slider')}
						>
							{mode === 'slider' ? $i18n.t('Slider') : $i18n.t('Menu')}
						</button>
					{/each}
				</div>
			</div>
			<div>
				<span class="text-xs font-normal text-gray-600 dark:text-gray-400"
					>{$i18n.t('Options')}</span
				>
				<div class="divide-y divide-gray-100/60 dark:divide-gray-850/60" use:sortable={moveOption}>
					{#each options as option, index (option.id)}
						<div class="py-1.5">
							<div class="flex items-center gap-1">
								<button
									type="button"
									class={`${actionClass} sort-handle cursor-grab`}
									aria-label={`${$i18n.t('Reorder')} ${option.label || $i18n.t('option')}`}
									title={$i18n.t('Drag or use the up and down arrow keys to reorder')}
									on:keydown={(event) => keyboardMove(event, index, moveOption)}
									><EllipsisVertical className="size-4" /></button
								>
								<input
									class={inputClass}
									aria-label={$i18n.t('Option name')}
									use:focus
									placeholder={$i18n.t('Option name')}
									bind:value={option.label}
									required
								/>
								<button
									type="button"
									class="flex shrink-0 items-center justify-center rounded text-gray-400 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
									aria-label={`${$i18n.t('Remove')} ${option.label || $i18n.t('option')}`}
									on:click={() => {
										options = options.filter((item) => item.id !== option.id);
										if (defaultOption === option.id) defaultOption = '';
									}}><XMark className="size-3" /></button
								>
							</div>
							<div class="pl-8"><CustomParams compact bind:value={option.params} /></div>
						</div>
					{/each}
				</div>
				<button
					type="button"
					class="mt-1 flex items-center gap-1.5 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
					on:click={addOption}
				>
					<Plus className="size-3" />
					<span>{$i18n.t('Add option')}</span>
				</button>
			</div>
			{#if display === 'slider' && options.length < 2}
				<p class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Add at least two options for a slider.')}
				</p>
			{/if}
			<div class="flex justify-end gap-1.5 pt-1 text-sm font-medium">
				<button
					type="button"
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 hover:bg-gray-100 dark:hover:bg-gray-850"
					on:click={() => (show = false)}>{$i18n.t('Cancel')}</button
				>
				<button
					type="submit"
					disabled={!label.trim() ||
						!options.length ||
						(display === 'slider' && options.length < 2) ||
						options.some((option) => !option.label.trim())}
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					>{$i18n.t('Apply')}</button
				>
			</div>
		</form>
	</div>
</Modal>
