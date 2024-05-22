<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { goto } from '$app/navigation';
	import { mobile, showSidebar } from '$lib/stores';

	const i18n = getContext('i18n');

	export let className = ' w-[12rem]';
	export let selectedChatId: string | null = null;

	let show = false;
	

</script>

<DropdownMenu.Root
	bind:open={show}
>
	<DropdownMenu.Trigger class="relative w-full flex">
		<div class="self-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-5"
			>
				<path
					d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
				/>
				<path
					d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
				/>
			</svg>
		</div>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content
		class="z-[60] {className} justify-start rounded-lg border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
		transition={flyAndScale}
		side={'bottom-end'}
		sideOffset={15}
	>
		<div class="p-1 py-2 w-full">
			
			<a class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			id="sidebar-new-chat-button"
					href="/"
					draggable="false"
					on:click={async () => {
						show = false;
						selectedChatId = null;

						await goto('/');
						const newChatButton = document.getElementById('new-chat-button');
						setTimeout(() => {
							newChatButton?.click();

							if ($mobile) {
								showSidebar.set(false);
							}
						}, 0);
					}}
			>
				<div class="self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-5"
					>
						<path
							d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
						/>
						<path
							d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
						/>
					</svg>
				</div>
				<div
					
				>
					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('New chat')}</div>
					</div>
				</div>
			</a>
			<div class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition">
				<a
					
					href="/"
					
				>
					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('LUAT PHAP')}</div>
					</div>
				</a>
			</div>
			<div class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition">
				<a
					
					href="/"
					
				>
					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('PHAT PHAP')}</div>
					</div>
				</a>
			</div>
			<div class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition">
				<a
					
					href="/"
					
				>
					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('FAQ')}</div>
					</div>
				</a>
			</div>
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>

<style>
	.scrollbar-none:active::-webkit-scrollbar-thumb,
	.scrollbar-none:focus::-webkit-scrollbar-thumb,
	.scrollbar-none:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-none::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
