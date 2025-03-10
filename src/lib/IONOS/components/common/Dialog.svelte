<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let title = '';
	export let show = false;
	export let closable = true;
	export let dialogId = 'dialog';

	let el: HTMLDialogElement|null = null;

	$: if (show) {
		el?.showModal();
	} else {
		el?.close();
	}
</script>

<dialog
	bind:this={el}
	class="fixed top-0 right-0 left-0 bottom-0 m-0 bg-black/20 h-screen max-w-[100vw] w-[100vw] max-h-[100dvh] justify-center items-center z-[99999999] overflow-hidden overscroll-contain"
	class:flex={show}
>
	<div
		data-id={`dialog-${dialogId}`}
		class="flex flex-col bg-white rounded-xl"
	>
		<div class="flex items-center border-gray-100" class:border-b={closable}>
			<div
				data-id={`dialog-title-${dialogId}`}
				class="grow py-7 px-7 cursor-default font-semibold text-nowrap overflow-hidden text-ellipsis"
			>
				{title}
			</div>
			{#if closable}
				<div class="px-6 py-5">
					<button
						data-id={`dialog-close-${dialogId}`}
						class="w-4 h-4"
						on:click={() => dispatch('close')}
					>
						<XMark className="w-5 h-5" />
					</button>
				</div>
			{/if}
		</div>

		<div
			data-id={`dialog-content-${dialogId}`}
			class="px-3 pb-4"
		>
			<slot />
		</div>
	</div>
</dialog>
