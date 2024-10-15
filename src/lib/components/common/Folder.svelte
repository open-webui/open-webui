<script>
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Collapsible from './Collapsible.svelte';

	export let open = true;
	export let name = '';
</script>

<div>
	<Collapsible
		bind:open
		className="w-full"
		buttonClassName="w-full"
		on:change={(e) => {
			dispatch('change', e.detail);
		}}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="mx-2 w-full"
			on:dragenter={(e) => {
				e.stopPropagation();
			}}
			on:drop={(e) => {
				console.log('Dropped on the Button');
			}}
			on:dragleave={(e) => {}}
		>
			<button
				class="w-full py-1 px-1.5 rounded-md flex items-center gap-1 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			>
				<div class="text-gray-300">
					{#if open}
						<ChevronDown className=" size-3" strokeWidth="2.5" />
					{:else}
						<ChevronRight className=" size-3" strokeWidth="2.5" />
					{/if}
				</div>

				<div class="translate-y-[0.5px]">
					{name}
				</div>
			</button>
		</div>

		<div slot="content">
			<slot></slot>
		</div>
	</Collapsible>
</div>
