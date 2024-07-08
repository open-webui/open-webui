<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	import XMark from '$lib/components/icons/XMark.svelte';
</script>

<div class=" dark:text-white">
	<div class="mb-2 flex justify-between items-center">
		<div class=" text-xl font-medium font-primary">Chat Controls</div>

		<div>
			<button
				on:click={() => {
					dispatch('close');
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>
	</div>

	<div>coming soon</div>
</div>
