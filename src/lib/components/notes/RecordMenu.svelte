<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Mic from '../icons/Mic.svelte';
	import CursorArrowRays from '../icons/CursorArrowRays.svelte';
	import CloudArrowUp from '../icons/CloudArrowUp.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onRecord = () => {};
	export let onCaptureAudio = () => {};
	export let onUpload = () => {};

	const dispatch = createEventDispatcher();
</script>

<Dropdown
	bind:show
	sideOffset={8}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[170px] font-primary">
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
		</DropdownMenu>
	</div>
</Dropdown>
