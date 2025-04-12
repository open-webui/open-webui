<script lang="ts">
	import { getContext } from 'svelte';
	import { onClickOutside } from '$lib/utils';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import WebSearchIcon from '$lib/components/icons/WebSearchIcon.svelte';
	import ImageGenerateIcon from '$lib/components/icons/ImageGenerateIcon.svelte';
	import CodeInterpreterIcon from '$lib/components/icons/CodeInterpreterIcon.svelte';

	const i18n = getContext('i18n');

	export let capabilities = {
		websearch: false,
		image_generation: false,
		code_interpreter: false,
		vision: false,
		// usage: false,
		citations: false
	};

	const capabilityIcons = {
		websearch: WebSearchIcon,
		image_generation: ImageGenerateIcon,
		code_interpreter: CodeInterpreterIcon
	};

	let showCapabilitiesDropdown = false;
	let dropdownRef;
</script>

<div class="my-1" use:onClickOutside={() => (showCapabilitiesDropdown = false)}>
	<div class="relative" bind:this={dropdownRef}>
		<button
			type="button"
			class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2 ${
				showCapabilitiesDropdown ? 'border' : ''
			} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
			on:click={() => (showCapabilitiesDropdown = !showCapabilitiesDropdown)}
		>
			<span class="text-gray-500 dark:text-customGray-100">{$i18n.t('Chat View')}</span>
			<ChevronDown className="size-3" />
		</button>

		{#if showCapabilitiesDropdown}
			<div
				class="max-h-60 pb-1 overflow-y-auto absolute z-50 w-full -mt-1 bg-white dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
			>
				<hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
				<div class="px-1">
					{#each Object.keys(capabilities) as capability}
						<div
							role="button"
							tabindex="0"
							class="flex items-center rounded-xl w-full justify-between px-3 py-2 hover:bg-gray-100 dark:hover:bg-customGray-950 cursor-pointer text-sm dark:text-customGray-100"
						>
                            <div class="flex items-center gap-2">
                                {#if capabilityIcons[capability]}
                                    <svelte:component
                                        this={capabilityIcons[capability]}
                                        class="size-4 text-gray-500 dark:text-gray-300"
                                    />
                                {/if}
                                <span class="capitalize">{capability.replace(/_/g, ' ')}</span>
                            </div>
							<Checkbox
								state={capabilities[capability] ? 'checked' : 'unchecked'}
								on:change={(e) => {
									e.stopPropagation();
									capabilities[capability] = e.detail === 'checked';
								}}
							/>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>
