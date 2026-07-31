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
	align="end"
	sideOffset={8}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[170px] ">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={async () => {
					onRecord();
					show = false;
				}}
			>
				<div class="self-center">
					<Mic className="size-3.5" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Record')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onCaptureAudio();
					show = false;
				}}
			>
				<div class="self-center">
					<CursorArrowRays className="size-3.5" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Capture Audio')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload();
					show = false;
				}}
			>
				<div class="self-center">
					<CloudArrowUp className="size-3.5" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Upload Audio')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
