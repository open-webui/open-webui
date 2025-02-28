<script lang="ts">
	import Spinner from './Spinner.svelte';

	interface Props {
		show?: boolean;
		content?: string;
		opacity?: number;
		children?: import('svelte').Snippet;
	}

	let { show = false, content = '', opacity = 1, children }: Props = $props();
</script>

<div class="relative">
	{#if show}
		<div class="absolute w-full h-full flex">
			<div
				style:inset="-10px"
				style:backdrop-filter="blur(5px)"
				style:opacity
				class="absolute rounded-sm"
			></div>

			<div class="flex w-full flex-col justify-center">
				<div class=" py-3">
					<Spinner className="ml-2" />
				</div>

				{#if content !== ''}
					<div class="text-center text-gray-100 text-xs font-medium z-50">
						{content}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	{@render children?.()}
</div>
