<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let logoImageUrl = '';
	export let name = '';
	export let imageClassName =
		'w-24 h-24 md:w-32 md:h-32 rounded-xl object-cover border border-gray-200 dark:border-gray-700';

	let fileInput: HTMLInputElement;

	const setLogo = (value: string) => {
		logoImageUrl = value;
		dispatch('change', { value });
	};

	const handleFileChange = () => {
		const files = fileInput.files ?? [];
		if (!files.length) return;

		const file = files[0];
	if (
		!['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
			file.type
		)
	) {
		toast.error($i18n.t('Unsupported file type.'));
		return;
	}

		const reader = new FileReader();
		reader.onload = (event) => {
			const src = `${event.target?.result ?? ''}`;
			if (!src) return;

			const img = new Image();
			img.src = src;
			img.onload = () => {
				const canvas = document.createElement('canvas');
				const ctx = canvas.getContext('2d');
				if (!ctx) return;

				const aspectRatio = img.width / img.height;
				let newWidth;
				let newHeight;

				if (aspectRatio > 1) {
					newWidth = 250 * aspectRatio;
					newHeight = 250;
				} else {
					newWidth = 250;
					newHeight = 250 / aspectRatio;
				}

				canvas.width = 250;
				canvas.height = 250;

				const offsetX = (250 - newWidth) / 2;
				const offsetY = (250 - newHeight) / 2;
				ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

				setLogo(canvas.toDataURL('image/jpeg'));
				fileInput.value = '';
			};
		};

		reader.readAsDataURL(file);
	};
</script>

<input
	id="tenant-logo-input"
	bind:this={fileInput}
	type="file"
	hidden
	accept="image/*"
	on:change={handleFileChange}
/>

<div class="flex flex-col items-start gap-2">
	<button
		type="button"
		class="relative rounded-2xl bg-white/40 dark:bg-gray-900/60 p-1"
		on:click={() => {
			fileInput.click();
		}}
	>
		<img
			src={logoImageUrl || generateInitialsImage(name || 'Tenant')}
			alt={$i18n.t('Logo Image URL')}
			class={imageClassName}
		/>

		<div class="absolute bottom-1 right-1 rounded-full bg-white text-gray-600 p-1 shadow">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
				<path
					fill-rule="evenodd"
					d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
	</button>

	<div class="flex flex-wrap gap-2 text-xs">
		<button
			type="button"
			class="rounded-lg px-2 py-1 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
			on:click={() => {
				setLogo('');
			}}>{$i18n.t('Remove')}</button
		>
		<button
			type="button"
			class="rounded-lg px-2 py-1 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
			on:click={() => {
				if (canvasPixelTest()) {
					setLogo(generateInitialsImage(name || 'Tenant'));
				} else {
					toast.info(
						$i18n.t(
							'Fingerprint spoofing detected: Unable to use initials as avatar. Defaulting to default profile image.'
						)
					);
				}
			}}>{$i18n.t('Initials')}</button
		>
	</div>
</div>
