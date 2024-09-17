<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { slide, fade } from 'svelte/transition';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import { employeeType } from '$lib/stores';

	const i18n = getContext('i18n');

	let showDropdown = false;
	let typeDropdownEl;
	let typeDropdownTrigger;
	// let employeeType = 'Staff';

	const handleOutsideClick = (evt) => {
		// click elements other than tigger button or dropdown menu itself when dropdown shows

		if (
			typeDropdownEl &&
			!typeDropdownEl.contains(evt.target) &&
			showDropdown &&
			!typeDropdownTrigger.contains(evt.target)
		) {
			showDropdown = false;
		}
	};

	onMount(() => {
		document.addEventListener('click', handleOutsideClick);
		return () => {
			document.removeEventListener('click', handleOutsideClick);
		};
	});
</script>

<div class="relative">
	<div
		class=" flex rounded-full py-1 px-3 w-full bg-white/80 text-gray-600 hover:text-gray-900 hover:bg-white transition"
		bind:this={typeDropdownTrigger}
	>
		I'm 
		<Tooltip content={'Switch user type'}>
			<button
				class="rounded-full px-2.5 bg-blue-500 text-white ml-2"
				on:click={() => {
					showDropdown = !showDropdown;
				}}>{$employeeType}</button
			>
		</Tooltip>
	</div>
	{#if showDropdown}
		<div
			id="dropdownDots"
			class="absolute z-40 top-[40px] right-0 rounded-lg shadow w-[100px] bg-white dark:bg-gray-900"
			transition:fade|slide={{ duration: 500 }}
			bind:this={typeDropdownEl}
		>
			{#each ['Staff', 'Faculty', 'Both'] as type}
				<div class="p-1 py-2 w-full">
					<button
						class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 disabled:bg-blue-500 disabled:text-white dark:hover:bg-gray-800 transition"
						disabled={$employeeType == type}
						on:click={async () => {
							showDropdown = false;
							toast('Swich user type will start a new chat. Would you like to continue?', {
								action: {
									label: 'Confirm',
									onClick: async () => {
										await employeeType.set(type);
										const newChatButton = document.getElementById('new-chat-button');
										setTimeout(() => {
											newChatButton?.click();
										}, 0);
									}
								}
							});
						}}
					>
						<div class=" self-center font-medium">{type}</div>
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
