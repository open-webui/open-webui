<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let message;

	const LIKE_REASONS = [
		`Accurate information`,
		`Followed instructions perfectly`,
		`Showcased creativity`,
		`Positive attitude`,
		`Attention to detail`,
		`Thorough explanation`,
		`Other`
	];

	const DISLIKE_REASONS = [
		`Don't like the style`,
		`Not factually correct`,
		`Didn't fully follow instructions`,
		`Refused when it shouldn't have`,
		`Being Lazy`,
		`Other`
	];

	let reasons = [];
	let selectedReason = null;
	let comment = '';

	$: if (message.annotation.rating === 1) {
		reasons = LIKE_REASONS;
	} else if (message.annotation.rating === -1) {
		reasons = DISLIKE_REASONS;
	}

	onMount(() => {
		selectedReason = message.annotation.reason;
		comment = message.annotation.comment;
	});

	const submitHandler = () => {
		console.log('submitHandler');

		message.annotation.reason = selectedReason;
		message.annotation.comment = comment;

		dispatch('submit');

		toast.success('Thanks for your feedback!');
		show = false;
	};
</script>

<div class=" my-2.5 rounded-xl px-4 py-3 border dark:border-gray-850">
	<div class="flex justify-between items-center">
		<div class=" text-sm">Tell us more:</div>

		<button
			on:click={() => {
				show = false;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="size-4"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	{#if reasons.length > 0}
		<div class="flex flex-wrap gap-2 text-sm mt-2.5">
			{#each reasons as reason}
				<button
					class="px-3.5 py-1 border dark:border-gray-850 dark:hover:bg-gray-850 {selectedReason ===
					reason
						? 'dark:bg-gray-800'
						: ''} transition rounded-lg"
					on:click={() => {
						selectedReason = reason;
					}}
				>
					{reason}
				</button>
			{/each}
		</div>
	{/if}

	<div class="mt-2">
		<textarea
			bind:value={comment}
			class="w-full text-sm px-1 py-2 bg-transparent outline-none resize-none rounded-xl"
			placeholder="Feel free to add specific details"
			rows="2"
		/>
	</div>

	<div class="mt-2 flex justify-end">
		<button
			class=" bg-emerald-700 text-white text-sm font-medium rounded-lg px-3.5 py-1.5"
			on:click={() => {
				submitHandler();
			}}
		>
			Submit
		</button>
	</div>
</div>
