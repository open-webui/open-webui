<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onEdit = () => {};
	export let onChat = () => {};

	export let onChange = () => {};
</script>

<Dropdown
	bind:show
	align="end"
	sideOffset={8}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[170px] font-primary">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={async () => {
					onEdit();
					show = false;
				}}
			>
				<div class="self-center">
					<Sparkles className="size-3.5" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Enhance')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onChat();
					show = false;
				}}
			>
				<div class="self-center">
					<ChatBubbleOval className="size-3.5" strokeWidth="2" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Chat')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
