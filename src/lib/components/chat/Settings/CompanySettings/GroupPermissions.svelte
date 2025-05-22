<script lang="ts">
	import { getContext, createEventDispatcher, onMount  } from 'svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import PermissionIcon from '$lib/components/icons/PermissionIcon.svelte';
	import { onClickOutside } from '$lib/utils';
	import WebSearchIcon from '$lib/components/icons/WebSearchIcon.svelte';
	import ImageGenerateIcon from '$lib/components/icons/ImageGenerateIcon.svelte';
	import CodeInterpreterIcon from '$lib/components/icons/CodeInterpreterIcon.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
    import RenameIcon from '$lib/components/icons/RenameIcon.svelte';
    
    
    const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

    export let group;

	let showDropdown = false;
	let hoveringGroup = false;
	let hoveringSubmenu = false;

    

	$: showSubmenu = hoveringGroup || hoveringSubmenu;
	let root;

	let submenuX = 0;
	let submenuY = 0;
	let groupTriggerEl: HTMLElement;

    let initialized = false;

	let capabilities = {
		web_search: true,
		image_generation: true,
		code_interpreter: true
	};

	const capabilityIcons = {
		web_search: WebSearchIcon,
		image_generation: ImageGenerateIcon,
		code_interpreter: CodeInterpreterIcon
	};
   
    $: {
        if(group && !initialized){
            if(group.permissions) {
            capabilities = {
		        web_search: group.permissions.features.web_search,
		        image_generation: group.permissions.features.image_generation,
		        code_interpreter: group.permissions.features.code_interpreter
	        };
        }
            initialized = true;
        }
    }

</script>

<div>
	<div bind:this={root} class="relative w-full h-4" use:onClickOutside={() => (showDropdown = false)}>
		<div
		on:click={() => (showDropdown = !showDropdown)}
	>
		<slot/>
	</div>
		{#if showDropdown}
			<div
				class="w-[10rem] flex flex-col absolute md:left-0 right-0 bg-lightGray-300 dark:bg-customGray-900 px-1 py-2 border border-lightGray-400 dark:border-customGray-700 rounded-lg z-10"
			>
				<button
					type="button"
					on:click={() => {
                        dispatch('editName')
                    }}
					class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
				>
					<RenameIcon />
					<div class="flex items-center">{$i18n.t('Rename')}</div>
				</button>
				<button
					type="button"
					class="relative"
					bind:this={groupTriggerEl}
					on:mouseenter={() => {
						hoveringGroup = true;
						if (groupTriggerEl) {
							const rect = groupTriggerEl.getBoundingClientRect();
							const screenWidth = window.innerWidth;
							if (screenWidth < 1290) {
								// submenuX = rect.left - 178;
								submenuX = -183;
							} else {
								// submenuX = rect.right + 8;
								submenuX = 158;
							}
							// submenuY = rect.top - 40;
							submenuY = -40;
							showSubmenu = true;
						}
					}}
					on:mouseleave={() => {
						hoveringGroup = false;
						setTimeout(() => {
							if (!hoveringSubmenu) showSubmenu = false;
						}, 100);
					}}
				>
					<button
						on:click={() => (showDropdown = false)}
						class="w-full flex justify-between gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
					>	<div class="flex items-center gap-2">
							<PermissionIcon />
							<div class="flex items-center">{$i18n.t('Permission')}</div>
						</div>
						<svg
							width="4"
							height="7"
							viewBox="0 0 4 7"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M3.9999 3.39941C3.9999 3.53267 3.94978 3.66592 3.84237 3.77113L1.31467 6.24687C1.10701 6.45026 0.763304 6.45026 0.555646 6.24687C0.347988 6.04348 0.347988 5.70684 0.555646 5.50345L2.70383 3.39941L0.555646 1.29538C0.347988 1.09199 0.347988 0.755346 0.555645 0.551957C0.763303 0.348567 1.10701 0.348567 1.31467 0.551957L3.84237 3.0277C3.94978 3.1329 3.9999 3.26616 3.9999 3.39941Z"
								fill="currentColor"
							/>
						</svg>
					</button>
					<div
						class="absolute left-full top-0 w-4 h-full z-10"
						on:mouseenter={() => (hoveringSubmenu = true)}
						on:mouseleave={() => (hoveringSubmenu = false)}
					></div>
					<div
						class="absolute -left-4 top-0 w-4 h-full z-10"
						on:mouseenter={() => (hoveringSubmenu = true)}
						on:mouseleave={() => (hoveringSubmenu = false)}
					></div>

					<!-- Submenu -->
					{#if showSubmenu}
						<button
							type="button"
							class="w-[11rem] absolute dark:bg-customGray-900 border px-1 py-2 border-lightGray-400 bg-lightGray-300 dark:border-customGray-700 rounded-xl shadow z-20 min-w-30"
							style="top: {submenuY}px; left: {submenuX}px"
							on:mouseenter={() => (hoveringSubmenu = true)}
							on:mouseleave={() => {
								hoveringSubmenu = false;
								showSubmenu = false;
							}}
						>
							{#each Object.keys(capabilities) as capability}
								<div
									role="button"
									tabindex="0"
									class="flex items-center rounded-xl w-full justify-start px-2 py-2 hover:bg-lightGray-700 dark:hover:bg-customGray-950 cursor-pointer text-xs dark:text-customGray-100"
								>
									<Checkbox
										state={capabilities[capability] ? 'checked' : 'unchecked'}
										on:change={(e) => {
											e.stopPropagation();
											capabilities[capability] = e.detail === 'checked';
                                            dispatch('changePermissions', capabilities)
										}}
									/>
									<div class="flex items-center gap-2 ml-2">
										{#if capabilityIcons[capability]}
											<svelte:component this={capabilityIcons[capability]} className="size-4" />
										{/if}
										<span class="capitalize">{capability.replace(/_/g, ' ')}</span>
									</div>
								</div>
							{/each}
						</button>
					{/if}
				</button>
				<button
					type="button"
					on:click={() => {
                        dispatch('deleteGroup')
                    }}
					class="flex gap-2 items-center px-3 py-2 text-xs text-[#F65351] font-medium cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
				>
					<DeleteIcon />
					<div class="flex items-center">{$i18n.t('Delete group')}</div>
				</button>
			</div>
		{/if}
	</div>
</div>
