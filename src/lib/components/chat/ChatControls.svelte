<script lang="ts">
	import { slide } from 'svelte/transition';
	import Modal from '../common/Modal.svelte';
	import Controls from './Controls/Controls.svelte';
	import { onMount } from 'svelte';

	export let show = false;

	let largeScreen = false;

	onMount(() => {
		// listen to resize 1024px
		const mediaQuery = window.matchMedia('(min-width: 1024px)');

		const handleMediaQuery = (e) => {
			if (e.matches) {
				largeScreen = true;
			} else {
				largeScreen = false;
			}
		};

		mediaQuery.addEventListener('change', handleMediaQuery);

		handleMediaQuery(mediaQuery);

		return () => {
			mediaQuery.removeEventListener('change', handleMediaQuery);
		};
	});
</script>

{#if largeScreen}
	<div
		class="fixed h-screen max-h-[100dvh] min-h-screen z-50 top-0 right-0 {show
			? 'w-[28rem]'
			: 'w-0 translate-x-[28rem] '} transition"
	>
		<div class="px-6 pt-14 pb-8 h-full">
			<div
				class=" px-5 py-4 h-full dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl shadow-lg"
			>
				<Controls
					on:close={() => {
						show = false;
					}}
				/>
			</div>
		</div>
	</div>
{:else}
	<Modal bind:show>
		<div class="  px-5 py-4 h-full">
			<Controls
				on:close={() => {
					show = false;
				}}
			/>
		</div>
	</Modal>
{/if}
