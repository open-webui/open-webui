<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';

	import Mic from '../icons/Mic.svelte';
	import CursorArrowRays from '../icons/CursorArrowRays.svelte';
	import DocumentArrowUp from '../icons/DocumentArrowUp.svelte';
	import CloudArrowUp from '../icons/CloudArrowUp.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onRecord = () => {};
	export let onCaptureAudio = () => {};
	export let onUpload = () => {};

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} text-sm rounded-xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					onRecord();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<Mic className="size-4" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Record')}</div>
			</button>

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					onCaptureAudio();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<CursorArrowRays className="size-4" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Capture Audio')}</div>
			</button>

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					onUpload();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<CloudArrowUp className="size-4" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Upload Audio')}</div>
			</button>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
