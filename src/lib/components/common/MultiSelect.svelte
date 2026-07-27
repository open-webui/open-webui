<script lang="ts">
	import { tick, createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const dispatch = createEventDispatcher();

	export let value: string[] = [];
	export let options: ({ label?: string; value: string } | string)[] = [];
	export let placeholder = '';
	export let className = '';

	let open = false;
	let triggerEl;
	let contentEl;

	$: items = options.map((option) =>
		typeof option === 'object' && option !== null
			? { value: option.value, label: option.label ?? option.value }
			: { value: option, label: option }
	);

	$: selectedValues = Array.isArray(value) ? value : [];
	$: selectedLabels = items
		.filter((item) => selectedValues.includes(item.value))
		.map((item) => item.label);

	const toggleItem = (itemValue) => {
		const current = Array.isArray(value) ? value : [];
		value = current.includes(itemValue)
			? current.filter((v) => v !== itemValue)
			: [...current, itemValue];
		dispatch('change');
	};

	/** Svelte action: moves the node to document.body (portal) */
	function portal(node) {
		document.body.appendChild(node);
		return {
			destroy() {
				if (node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}

	function positionContent() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '9999';
		contentEl.style.top = `${rect.bottom + 4}px`;
		contentEl.style.left = `${rect.left}px`;
		contentEl.style.minWidth = `${rect.width}px`;
	}

	async function toggleOpen() {
		open = !open;
		if (open) {
			await tick();
			positionContent();
		}
	}

	function handleWindowClick(event) {
		if (!open) return;
		if (triggerEl?.contains(event.target)) return;
		if (contentEl?.contains(event.target)) return;
		open = false;
	}

	function handleKeydown(event) {
		if (event.key === 'Escape' && open) {
			open = false;
		}
	}
</script>

<svelte:window
	on:click={handleWindowClick}
	on:keydown={handleKeydown}
	on:scroll|capture={positionContent}
	on:resize={positionContent}
/>

<button
	bind:this={triggerEl}
	class={className}
	aria-label={placeholder}
	type="button"
	on:click={toggleOpen}
>
	<div class="flex w-full items-center justify-between gap-2">
		<span class="truncate text-left {selectedLabels.length ? '' : 'text-gray-500'}">
			{selectedLabels.length ? selectedLabels.join(', ') : placeholder}
		</span>

		<ChevronDown className="size-3 shrink-0" strokeWidth="2.5" />
	</div>
</button>

{#if open}
	<div use:portal bind:this={contentEl} transition:flyAndScale>
		<div
			class="rounded-2xl min-w-[170px] max-h-72 overflow-y-auto p-1 border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		>
			{#each items as item}
				<button
					class="flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					type="button"
					on:click={() => toggleItem(item.value)}
				>
					<div
						class="size-3.5 shrink-0 rounded-sm flex items-center justify-center outline -outline-offset-1 outline-[1.5px] {selectedValues.includes(
							item.value
						)
							? 'bg-black outline-black text-white'
							: 'outline-gray-200 dark:outline-gray-600'}"
					>
						{#if selectedValues.includes(item.value)}
							<svg
								class="size-3"
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
									d="m5 12 4.7 4.5 9.3-9"
								/>
							</svg>
						{/if}
					</div>

					<span
						class="truncate {selectedValues.includes(item.value)
							? ''
							: 'text-gray-500 dark:text-gray-400'}"
					>
						{item.label}
					</span>
				</button>
			{/each}
		</div>
	</div>
{/if}
