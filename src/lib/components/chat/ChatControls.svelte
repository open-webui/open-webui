<script lang="ts">
	import { slide } from 'svelte/transition';
	import Modal from '../common/Modal.svelte';
	import Controls from './Controls/Controls.svelte';
	import { onMount } from 'svelte';
	import { mobile, showCallOverlay } from '$lib/stores';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';

	export let show = false;

	export let models = [];

	export let chatId = null;
	export let chatFiles = [];
	export let params = {};

	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let stopResponse: Function;
	export let files;
	export let modelId;

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

{#if !largeScreen}
	{#if $showCallOverlay}
		<div class=" absolute w-full h-screen max-h-[100dvh] flex z-[999] overflow-hidden">
			<div
				class="absolute w-full h-screen max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
			>
				<CallOverlay
					bind:files
					{submitPrompt}
					{stopResponse}
					{modelId}
					{chatId}
					{eventTarget}
					on:close={() => {
						show = false;
					}}
				/>
			</div>
		</div>
	{:else if show}
		<Drawer bind:show>
			<div class="  px-6 py-4 h-full">
				<Controls
					on:close={() => {
						show = false;
					}}
					{models}
					bind:chatFiles
					bind:params
				/>
			</div>
		</Drawer>
	{/if}
{:else if show}
	<div class=" absolute bottom-0 right-0 z-20 h-full pointer-events-none">
		<div class="pr-4 pt-14 pb-8 w-[24rem] h-full" in:slide={{ duration: 200, axis: 'x' }}>
			<div
				class="w-full h-full px-5 py-4 bg-white dark:shadow-lg dark:bg-gray-850 border border-gray-50 dark:border-gray-800 rounded-xl z-50 pointer-events-auto overflow-y-auto scrollbar-hidden"
			>
				{#if $showCallOverlay}
					<CallOverlay
						bind:files
						{submitPrompt}
						{stopResponse}
						{modelId}
						{chatId}
						{eventTarget}
						on:close={() => {
							show = false;
						}}
					/>
				{:else}
					<Controls
						on:close={() => {
							show = false;
						}}
						{models}
						bind:chatFiles
						bind:params
					/>
				{/if}
			</div>
		</div>
	</div>
{/if}
