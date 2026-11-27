<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount, tick } from 'svelte';

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronRight from './icons/ChevronRight.svelte';
	import Plus from './icons/Plus.svelte';

	const dispatch = createEventDispatcher();
	type AddHandler = () => void | Promise<void>;

	export let open = true;
	export let id = '';
	export let name = '';
	export let collapsible = true;
	export let className = '';
	export let buttonClassName = '';
	export let contentClassName = 'px-1.5';
	export let onAddLabel = '';
	export let onAdd: null | AddHandler = null;
	export let dragAndDrop = true;
	/** Shows the name as a text field; saving calls onRename. */
	export let editing = false;
	export let onRename: ((name: string) => void) | null = null;
	/** Whether the heading reorders the sidebar's sections; off for one nested in another. */
	export let sortHandle = true;
	/** Makes the heading draggable on its own, e.g. to reorder nested sections. */
	export let onHeadingDragStart: ((e: DragEvent) => void) | null = null;
	export let onHeadingDragEnd: (() => void) | null = null;

	let nameInput: HTMLInputElement | undefined;
	let nameDraft = '';
	$: if (editing && !nameInput) void startRename();

	const startRename = async () => {
		nameDraft = name;
		editing = true;
		await tick();
		nameInput?.focus();
		nameInput?.select();
	};

	const saveRename = () => {
		if (!editing) return;
		editing = false;
		const next = nameDraft.trim();
		if (next && next !== name) onRename?.(next);
	};

	let sectionElement: HTMLDivElement;
	let loaded = false;
	let draggedOver = false;

	const setOpen = (state: boolean) => {
		open = state;
		dispatch('change', state);
		localStorage.setItem(`${id}-folder-state`, `${state}`);
	};

	const onDragOver = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = true;
	};

	const onDrop = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();

		if (!sectionElement.contains(e.target as Node)) {
			return;
		}

		if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
			for (const item of Array.from(e.dataTransfer.items)) {
				if (item.kind === 'file') {
					const file = item.getAsFile();
					if (file && file.type === 'application/json') {
						const reader = new FileReader();
						reader.onload = async function (event) {
							try {
								const fileContent = JSON.parse(event.target?.result as string);
								open = true;
								dispatch('import', fileContent);
							} catch (error) {
								console.error('Error parsing JSON file:', error);
							}
						};
						reader.readAsText(file);
					}
				} else {
					open = true;
					try {
						const dataTransfer = e.dataTransfer.getData('text/plain');
						if (dataTransfer) {
							dispatch('drop', JSON.parse(dataTransfer));
						}
					} catch {
						// Ignore drops that are not sidebar JSON payloads.
					} finally {
						draggedOver = false;
					}
					break;
				}
			}
		}

		draggedOver = false;
	};

	const onDragLeave = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = false;
	};

	onMount(() => {
		const state = localStorage.getItem(`${id}-folder-state`);
		if (state !== null) {
			open = state === 'true';
		}

		loaded = true;

		if (!dragAndDrop) {
			return;
		}

		sectionElement.addEventListener('dragover', onDragOver);
		sectionElement.addEventListener('drop', onDrop);
		sectionElement.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		if (!dragAndDrop) {
			return;
		}

		sectionElement.removeEventListener('dragover', onDragOver);
		sectionElement.removeEventListener('drop', onDrop);
		sectionElement.removeEventListener('dragleave', onDragLeave);
	});
</script>

<div bind:this={sectionElement} class="relative {className}">
	{#if loaded}
		{#if draggedOver}
			<div
				class="pointer-events-none absolute inset-0 z-50 touch-none bg-base-1000/[0.02] ring-1 ring-inset ring-base-1000/10 dark:bg-base-0/[0.02] dark:ring-base-0/10"
			></div>
		{/if}

		{#if collapsible}
			<Collapsible bind:open className="w-full" buttonClassName="w-full" onChange={setOpen}>
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div
					class="flex items-center justify-between h-6 w-full pl-3.5 pr-1.5 shrink-0"
					data-section-handle={sortHandle ? '' : undefined}
					draggable={onHeadingDragStart && !editing ? 'true' : undefined}
					on:dragstart={(e) => onHeadingDragStart?.(e)}
					on:dragend={() => onHeadingDragEnd?.()}
				>
					<h2 class="flex flex-1 h-full">
						{#if editing}
							<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
							<div class="contents" on:click={(e) => e.stopPropagation()}>
								<input
									bind:this={nameInput}
									bind:value={nameDraft}
									class="flex-1 h-full min-w-0 bg-transparent text-xs text-base-500 dark:text-base-400 outline-hidden"
									on:blur={saveRename}
									on:keydown={(e) => {
										if (e.key === 'Enter') e.currentTarget.blur();
										if (e.key === 'Escape') {
											nameDraft = name;
											e.currentTarget.blur();
										}
									}}
								/>
							</div>
						{:else}
							<button
								type="button"
								class="group flex flex-1 h-full items-center gap-1 text-left text-xs text-base-400 hover:text-base-500 dark:text-base-500 dark:hover:text-base-400 transition-colors duration-100 {buttonClassName}"
								id="{id}-button"
								aria-expanded={open}
								aria-controls="{id}-content"
							>
								<span>{name}</span>
								<span
									class="flex opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-all duration-100"
									style="transform: rotate({open ? '90deg' : '0deg'})"
								>
									<ChevronRight className="size-[0.6875rem]" />
								</span>
							</button>
						{/if}
					</h2>

					<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
					<div class="contents" on:click={(e) => e.stopPropagation()}>
						<slot name="action" />
					</div>

					{#if onAdd}
						<button
							type="button"
							class="flex items-center justify-center w-7 h-7 rounded-lg text-base-300 hover:text-base-500 dark:text-base-600 dark:hover:text-base-400 transition-colors duration-100"
							aria-label={onAddLabel}
							on:click={(e) => {
								e.stopPropagation();
								onAdd();
							}}
						>
							<Tooltip content={onAddLabel}>
								<Plus className="size-3.5" />
							</Tooltip>
						</button>
					{/if}
				</div>

				<div id="{id}-content" slot="content" class="w-full {contentClassName}">
					<slot></slot>
				</div>
			</Collapsible>
		{:else}
			<slot></slot>
		{/if}
	{/if}
</div>
