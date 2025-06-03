<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount } from 'svelte';

	import { theme } from '$lib/stores';
	import { flyAndScale } from '$lib/utils/transitions';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import 'emoji-picker-element';

	const i18n = getContext('i18n');

	export let onClose: Function = () => {};
	export let uploadImage: Function = () => {};
	export let selectEmoji: Function = () => {};
	export let removeImage: Function = () => {};
	export let allowEmojiSelection = true;

	let emojiPicker;
	export let open = false;
	let selectedTab = 'upload';
	onMount(() => {
		if (emojiPicker) {
			emojiPicker.addEventListener('emoji-click', (event) => {
				selectEmoji(event.detail.unicode);
				open = false;
			});
		}
	});

	$: if (emojiPicker) {
		emojiPicker.addEventListener('emoji-click', (event) => {
			selectEmoji(event.detail.unicode);
			open = false;
		});
	}
</script>

<Dropdown
	bind:show={open}
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-fit rounded-tl-lg rounded-tr-lg  {selectedTab === 'emoji'
				? ''
				: 'rounded-lg'} border border-gray-300/30 dark:border-gray-700/50 z-[99999] bg-white dark:bg-gray-900 dark:text-white shadow-lg"
			sideOffset={8}
			side="right"
			align="start"
			transition={flyAndScale}
		>
			<div
				class="flex flex-1 flex-row justify-start px-2 pt-2 dark:text-white {selectedTab ===
				'upload'
					? 'border-b border-slate-200 dark:border-[#27272A]'
					: ''} min-w-[344px]"
			>
				<div
					class="{selectedTab === 'upload' ? 'border-b border-black dark:border-white' : ''} pb-1"
				>
					<button
						class="font-normal p-1 text-sm text-lightGray-100 dark:text-customGray-100 leading-5 {selectedTab === 'upload'
							? ' dark:text-white'
							: ''} rounded-md"
						on:click={async () => {
							selectedTab = 'upload';
						}}
					>
						<div class="flex items-center">{$i18n.t('Upload')}</div>
					</button>
				</div>
				{#if allowEmojiSelection}
					<div
						class="ml-1 {selectedTab === 'emoji'
							? 'border-b border-black dark:border-white'
							: ''} pb-1"
					>
						<button
							class="font-normal p-1 text-sm leading-5 text-lightGray-100 dark:text-customGray-100 {selectedTab === 'emoji'
								? ' dark:text-white'
								: ''} rounded-md"
							on:click={async () => {
								selectedTab = 'emoji';
							}}
						>
							<div class="flex items-center">{$i18n.t('Emojis')}</div>
						</button>
					</div>
				{/if}
				<button
					class="font-normal ml-auto p-1 pb-2 text-sm leading-5 rounded-md"
					on:click={async () => {
						removeImage();
					}}
				>
					<div class="flex items-center text-lightGray-100 dark:text-customGray-100">
						{$i18n.t('Remove')}
					</div>
				</button>
			</div>
			{#if selectedTab === 'emoji'}
				<div class="">
					<emoji-picker class={$theme} bind:this={emojiPicker} />
				</div>
			{:else if selectedTab === 'upload'}
				<div class="items-center text-center align-center">
					<button
						class="font-normal mt-4 px-3 py-2 text-sm leading-5 rounded-full border border-slate-200"
						on:click={async () => {
							uploadImage();
						}}
					>
						<div class="flex items-center text-lightGray-100 dark:text-customGray-100">{$i18n.t('Upload File')}</div>
					</button>
					<div class="font-normal text-lightGray-100  p-4 mb-1 text-sm leading-5 dark:text-customGray-200">
						{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}
					</div>
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>