<script lang="ts">
	import DOMPurify from 'dompurify';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';

	export let model = null;

	const tippyOptions = {
		interactive: true, // to enable keeping it open when hovered
		duration: [100, 100],
		offset: [75, -35], // to overlay the small model avatar image ([y, x] 🤷)
	};

	// The model description is supposed to be formatted in this format:
	// Subtitle
	//
	// Description
	const rawDescriptionParts = model?.info?.meta?.description?.split('\n\n') ?? [];
	const [subtitle, description] = rawDescriptionParts.map(DOMPurify.sanitize);
</script>

{#if subtitle && description}
<Tooltip
	theme="model-details"
	placement="left"
	tippyOptions={tippyOptions}
	allowHTML={true}
	content={`<div class="flex flex-row">
				<div class="flex-shrink-0 pr-4">
					<img class="w-24 h-24 object-cover rounded-full" src=${model?.info?.meta?.profile_image_url} alt="Model avatar image">
				</div>
				<div>
					<h1 class="text-base font-bold">${model?.name ?? ""}</h1>
					<h2 class="text-base mb-2">${subtitle}</h2>
					<p class="text-sm">${description}</p>
				</div>
			</div>`}
>
	<ProfileImage
		src={model?.info?.meta?.profile_image_url ?? ""}
		className={'size-8'}
	/>
</Tooltip>
{:else}
	<ProfileImage
		src={model?.info?.meta?.profile_image_url ?? ""}
		className={'size-8'}
	/>
{/if}

<style>
	:global([data-theme="model-details"]) {
		max-width: 450px !important; /* thanks tippy.js for using style 🙄 */
		padding: 10px;

		border-radius: 20px;

		background-color: #fff;
		color: #000;
		box-shadow: 0 0 5px #ccc, 5px 5px 20px #ccc;
	}
</style>

