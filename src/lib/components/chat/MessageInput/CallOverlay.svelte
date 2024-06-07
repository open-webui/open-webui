<script lang="ts">
	import { showCallOverlay } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	onMount(async () => {
		console.log('wip');
	});
</script>

<div class=" absolute w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
	>
		<div class="max-w-md w-full h-screen flex flex-col justify-between p-6">
			<div>
				<!-- navbar -->
			</div>

			<div class="flex justify-center items-center w-ull">
				<div class=" size-44 bg-black dark:bg-white rounded-full animate-pulse" />
			</div>

			<div class="flex justify-between items-center pb-2 w-full">
				<div>
					<button class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z"
							/>
						</svg>
					</button>
				</div>

				<div class=" line-clamp-1 text-sm font-medium">Listening...</div>

				<div>
					<button
						class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900"
						on:click={async () => {
							showCallOverlay.set(false);
						}}
						type="button"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-5"
						>
							<path
								d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
							/>
						</svg>
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
