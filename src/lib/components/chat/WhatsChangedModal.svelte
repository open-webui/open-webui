<script lang="ts">
	import Modal from '../common/Modal.svelte';
	import { Confetti } from 'svelte-confetti';
	import { WEBUI_NAME, WEB_UI_VERSION, RELEASE_NOTES } from '$lib/constants';
	import { config, showWhatsChanged } from '$lib/stores';

	function toggleVisibility() {
		showWhatsChanged.update((value) => !value);
	}
</script>

<Modal>
	<div class="px-5 py-4 dark:text-gray-300">
		<div class="flex justify-between items-start">
			<div class="text-xl font-bold">
				{WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button class="self-center" on:click={toggleVisibility}>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<div class=" pb-3 flex items-center mt-2">
			<div class="text-sm dark:text-gray-200">Release Notes</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<div class="text-sm dark:text-gray-200">
				{$config && $config.version ? $config.version : WEB_UI_VERSION}
			</div>
		</div>
		<hr class=" dark:border-gray-800" />
		<div class="p-4 overflow-y-scroll max-h-80">
			{#if RELEASE_NOTES.length === 0}
				<div class="pt-10 text-center font-bold">There are no notes given.</div>

				<div class="pb-10 text-center">
					Check
					<a class="text-blue-500" href="https://github.com/open-webui/open-webui" target="_blank">
						Open WebUI on GitHub</a
					> for more information.
				</div>
			{:else}
				{#each RELEASE_NOTES as { title, description }}
					<div class="mt-4">
						<div class="font-bold">{title}</div>
						<div>{description}</div>
					</div>
				{/each}
			{/if}
		</div>
		<div class="m-4 flex justify-end pt-3 text-sm font-medium">
			<button
				on:click={toggleVisibility}
				class=" rounded px-4 py-2 overflow-hidden group bg-green-600 relative hover:bg-gradient-to-r hover:from-green-600 hover:to-green-500 text-white hover:ring-2 hover:ring-offset-2 hover:ring-green-500 transition-all ease-out duration-300"
			>
				<span
					class="absolute right-0 w-8 h-32 -mt-12 transition-all duration-1000 transform translate-x-12 bg-white opacity-10 rotate-12 group-hover:-translate-x-40 ease"
				/>
				<span class="relative">Ok, let's go!</span>
			</button>
		</div>
	</div>
</Modal>
