<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';
	import Sparkles from '../icons/Sparkles.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onEdit = () => {};
	export let onChat = () => {};

	export let onChange = () => {};
</script>

<DropdownMenu.Root bind:open={show} onOpenChange={onChange}>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} text-sm rounded-xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
			sideOffset={8}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					onEdit();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<Sparkles className="size-4" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Enhance')}</div>
			</button>

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					onChat();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<ChatBubbleOval className="size-4" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Chat')}</div>
			</button>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
