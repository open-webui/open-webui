<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import Tooltip from '../Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let tag;
	export let onDelete = () => {};
</script>

{#if tag}
	<Tooltip content={tag.name}>
		<button
			aria-label={$i18n.t('Remove this tag from list')}
			class="relative group/tags px-1.5 py-[0.5px] gap-0.5 flex justify-between h-fit max-h-fit w-fit items-center rounded-lg bg-gray-500/20 text-gray-700 dark:text-gray-200 transition cursor-pointer"
			on:click={() => {
				onDelete();
			}}
		>
			<div class=" text-[0.7rem] font-medium self-center line-clamp-1 w-fit">
				{tag.name}
			</div>

			<div class="hidden group-hover/tags:block transition">
				<div class="rounded-full pl-[1px] backdrop-blur-sm h-full flex self-center cursor-pointer">
					<XMark className="size-3" strokeWidth="2.5" />
				</div>
			</div>
		</button>
	</Tooltip>
{/if}
