<script lang="ts">
	export let show = false;
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
	class="fixed top-0 right-0 left-0 bottom-0 m-0 bg-black/25 h-screen max-w-[100vw] w-[100vw] max-h-[100dvh] justify-center items-center z-[99999999] overflow-hidden overscroll-contain"
	class:flex={show}
>
	<div
		data-id={`dialog-${dialogId}`}
		class="flex flex-col bg-white relative shadow-xl rounded-2xl {$$props.class ?? 'p-[30px]'}"
	>
		<slot name="header" />

		<div
			data-id={`dialog-content-${dialogId}`}
			class=""
		>
			<slot name="content"/>
		</div>
	</div>
</dialog>
