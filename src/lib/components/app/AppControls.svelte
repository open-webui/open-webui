<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	let selected = '';
</script>

<div class="min-w-[4.5rem] bg-gray-50 dark:bg-gray-950 flex gap-2.5 flex-col pt-10">
	<div class="flex justify-center relative">
		{#if selected === 'home'}
			<div class="absolute top-0 left-0 flex h-full">
				<div class="my-auto rounded-r-lg w-1 h-8 bg-white"></div>
			</div>
		{/if}

		<Tooltip content="Home" placement="right">
			<button
				class=" cursor-pointer bg-gray-100 dark:bg-gray-850 {selected === 'home'
					? 'rounded-2xl'
					: 'rounded-full'}"
				on:click={() => {
					selected = 'home';
				}}
			>
				<img
					src="/static/splash.png"
					class="size-11 dark:invert p-1"
					alt="logo"
					draggable="false"
				/>
			</button>
		</Tooltip>
	</div>

	<div class="border-t border-gray-50 dark:border-gray-900 mx-3"></div>

	<div class="flex justify-center relative group">
		{#if selected === ''}
			<div class="absolute top-0 left-0 flex h-full">
				<div class="my-auto rounded-r-lg w-1 h-8 bg-white"></div>
			</div>
		{/if}
		<button
			class=" cursor-pointer bg-transparent"
			onclick={() => {
				selected = '';
			}}
		>
			<img
				src="/assets/images/adam.jpg"
				class="size-11 {selected === '' ? 'rounded-2xl' : 'rounded-full'}"
				alt="logo"
				draggable="false"
			/>
		</button>
	</div>

	<div class="flex justify-center relative group text-gray-400">
		<button class=" cursor-pointer p-2" onclick={() => {}}>
			<Plus className="size-5" strokeWidth="2" />
		</button>
	</div>
</div>
