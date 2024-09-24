<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let show = false;
	export let src = '';
	export let alt = '';

	let mounted = false;

	let previewElement = null;

	const downloadImage = (url, filename, prefixName = '') => {
		fetch(url)
			.then((response) => response.blob())
			.then((blob) => {
				const objectUrl = window.URL.createObjectURL(blob);
				const link = document.createElement('a');
				link.href = objectUrl;
				link.download = `${prefixName}${filename}`;
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);
				window.URL.revokeObjectURL(objectUrl);
			})
			.catch((error) => console.error('Error downloading image:', error));
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			show = false;
		}
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && previewElement) {
		document.body.appendChild(previewElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (previewElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(previewElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;

		if (previewElement) {
			document.body.removeChild(previewElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={previewElement}
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black text-white w-full min-h-screen h-screen flex justify-center z-[9999] overflow-hidden overscroll-contain"
	>
		<div class=" absolute left-0 w-full flex justify-between select-none">
			<div>
				<button
					class=" p-5"
					on:click={() => {
						show = false;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="w-6 h-6"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div>
				<button
					class=" p-5"
					on:click={() => {
						downloadImage(src, src.substring(src.lastIndexOf('/') + 1), alt);
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-6 h-6"
					>
						<path
							d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
						/>
						<path
							d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
						/>
					</svg>
				</button>
			</div>
		</div>
		<img {src} {alt} class=" mx-auto h-full object-scale-down select-none" draggable="false" />
	</div>
{/if}
