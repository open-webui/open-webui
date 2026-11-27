<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy } from 'svelte';

	import Photo from '$lib/components/icons/Photo.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	// The saved banner, cleared by Remove.
	export let src: string | null = null;
	// A new image, uploaded when the settings are saved.
	export let file: File | null = null;

	let input: HTMLInputElement;
	let preview: string | null = null;

	const setFile = (selected: File | null) => {
		if (preview) URL.revokeObjectURL(preview);
		preview = selected ? URL.createObjectURL(selected) : null;
		file = selected;
	};
	onDestroy(() => {
		if (preview) URL.revokeObjectURL(preview);
	});

	// Saved: the parent has uploaded the file and cleared it.
	$: if (!file && preview) setFile(null);

	const selectHandler = async () => {
		const selected = input.files?.[0];
		input.value = '';
		if (!selected) return;

		const candidate = URL.createObjectURL(selected);
		try {
			if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(selected.type))
				throw new Error($i18n.t('Background image must be PNG, JPEG, WebP, or GIF.'));
			if (selected.size > 5 * 1024 * 1024)
				throw new Error($i18n.t('Background image must be at most 5 MiB.'));
			const image = new Image();
			image.src = candidate;
			await image.decode().catch(() => {
				throw new Error($i18n.t('Invalid background image.'));
			});
			if (image.naturalWidth * image.naturalHeight > 25_000_000)
				throw new Error($i18n.t('Background image must be at most 25 megapixels.'));
			setFile(selected);
		} catch (error) {
			toast.error((error as Error).message);
		} finally {
			URL.revokeObjectURL(candidate);
		}
	};

	const buttonClass =
		'rounded-md px-1 py-1 text-xs font-normal text-base-500 transition hover:text-base-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:text-base-400 dark:hover:text-base-300';
</script>

<input
	bind:this={input}
	type="file"
	accept="image/png,image/jpeg,image/webp,image/gif"
	hidden
	on:change={selectHandler}
/>

<!-- Same header as the model editor. -->
<div>
	<div class="relative w-full {(preview ?? src) ? 'h-36' : 'h-20'}">
		{#if preview ?? src}
			<img
				src={preview ?? src}
				alt=""
				class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full rounded-xl object-cover"
			/>
		{:else}
			<div
				aria-hidden="true"
				class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full rounded-xl bg-base-100 dark:bg-base-850"
			></div>
		{/if}
	</div>

	<div
		class="relative flex min-w-0 flex-wrap items-center justify-between gap-x-3 px-3 {(preview ??
		src)
			? '-mt-14'
			: '-mt-9'}"
	>
		<slot />

		<div
			class="flex shrink-0 items-center gap-1"
			title={$i18n.t('PNG, JPEG, WebP, or GIF. Up to 5 MiB and 25 megapixels.')}
		>
			{#if preview ?? src}
				<button type="button" class={buttonClass} on:click={() => input.click()}
					>{$i18n.t('Change')}</button
				>
				<button
					type="button"
					class={buttonClass}
					on:click={() => {
						setFile(null);
						src = null;
					}}>{$i18n.t('Remove')}</button
				>
			{:else}
				<button
					type="button"
					class="flex items-center gap-1.5 {buttonClass}"
					on:click={() => input.click()}
				>
					<Photo className="size-3.5" />
					{$i18n.t('Add banner')}
				</button>
			{/if}
		</div>
	</div>
</div>
