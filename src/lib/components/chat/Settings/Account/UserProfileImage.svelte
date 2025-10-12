<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { getGravatarUrl } from '$lib/apis/utils';
	import { canvasPixelTest, generateInitialsImage } from '$lib/utils';

	import { WEBUI_BASE_URL } from '$lib/constants';

	export let profileImageUrl;
	export let user = null;

	export let imageClassName = 'size-14 md:size-18';

	let profileImageInputElement;
</script>

<input
	id="profile-image-input"
	bind:this={profileImageInputElement}
	type="file"
	hidden
	accept="image/*"
	on:change={(e) => {
		const files = profileImageInputElement.files ?? [];
		let reader = new FileReader();
		reader.onload = (event) => {
			let originalImageUrl = `${event.target.result}`;

			const img = new Image();
			img.src = originalImageUrl;

			img.onload = function () {
				const canvas = document.createElement('canvas');
				const ctx = canvas.getContext('2d');

				// Calculate the aspect ratio of the image
				const aspectRatio = img.width / img.height;

				// Calculate the new width and height to fit within 250x250
				let newWidth, newHeight;
				if (aspectRatio > 1) {
					newWidth = 250 * aspectRatio;
					newHeight = 250;
				} else {
					newWidth = 250;
					newHeight = 250 / aspectRatio;
				}

				// Set the canvas size
				canvas.width = 250;
				canvas.height = 250;

				// Calculate the position to center the image
				const offsetX = (250 - newWidth) / 2;
				const offsetY = (250 - newHeight) / 2;

				// Draw the image on the canvas
				ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

				// Get the base64 representation of the compressed image
				const compressedSrc = canvas.toDataURL('image/jpeg');

				// Display the compressed image
				profileImageUrl = compressedSrc;

				profileImageInputElement.files = null;
			};
		};

		if (
			files.length > 0 &&
			['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(files[0]['type'])
		) {
			reader.readAsDataURL(files[0]);
		}
	}}
/>

<div class="flex flex-col self-start group">
	<div class="self-center flex">
		<button
			class="relative rounded-full dark:bg-gray-700"
			type="button"
			on:click={() => {
				profileImageInputElement.click();
			}}
		>
			<img
				src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(user?.name)}
				alt="profile"
				class=" rounded-full {imageClassName} object-cover"
			/>

			<div class="absolute bottom-0 right-0 opacity-0 group-hover:opacity-100 transition">
				<div class="p-1 rounded-full bg-white text-black border-gray-100 shadow">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3"
					>
						<path
							d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
						/>
					</svg>
				</div>
			</div>
		</button>
	</div>
	<div class="flex flex-col w-full justify-center mt-2">
		<button
			class=" text-xs text-center text-gray-500 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
			type="button"
			on:click={async () => {
				profileImageUrl = `${WEBUI_BASE_URL}/user.png`;
			}}>{$i18n.t('Remove')}</button
		>

		<button
			class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
			type="button"
			on:click={async () => {
				if (canvasPixelTest()) {
					profileImageUrl = generateInitialsImage(user?.name);
				} else {
					toast.info(
						$i18n.t(
							'Fingerprint spoofing detected: Unable to use initials as avatar. Defaulting to default profile image.'
						),
						{
							duration: 1000 * 10
						}
					);
				}
			}}>{$i18n.t('Initials')}</button
		>

		<button
			class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
			type="button"
			on:click={async () => {
				const url = await getGravatarUrl(localStorage.token, user?.email);

				profileImageUrl = url;
			}}>{$i18n.t('Gravatar')}</button
		>
	</div>
</div>
