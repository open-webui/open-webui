<script lang="ts">
	import { onMount } from 'svelte';
	import { Confetti } from 'svelte-confetti';

	import { WEBUI_NAME, config } from '$lib/stores';

	import { WEBUI_VERSION } from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';

	export let show = false;

	let changelog = null;

	onMount(async () => {
		const res = await getChangelog();
		changelog = res;
	});
</script>

<Modal bind:show>
	<div class="px-5 py-4 dark:text-gray-300">
		<div class="flex justify-between items-start">
			<div class="text-xl font-bold">
				What’s New in {$WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">Release Notes</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<div class="text-sm dark:text-gray-200">
				v{WEBUI_VERSION}
			</div>
		</div>
	</div>

	<hr class=" dark:border-gray-800" />

	<div class=" w-full p-4 px-5">
		<div class=" overflow-y-scroll max-h-80">
			<div class="mb-3">
				{#if changelog}
					{#each Object.keys(changelog) as version}
						<div class=" mb-3 pr-2">
							<div class="font-bold text-xl mb-1 dark:text-white">
								v{version} - {changelog[version].date}
							</div>

							<hr class=" dark:border-gray-800 my-2" />

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div class="">
									<div
										class="font-bold uppercase text-xs {section === 'added'
											? 'text-white bg-blue-600'
											: section === 'fixed'
											? 'text-white bg-green-600'
											: section === 'changed'
											? 'text-white bg-yellow-600'
											: section === 'removed'
											? 'text-white bg-red-600'
											: ''}  w-fit px-3 rounded-full my-2.5"
									>
										{section}
									</div>

									<div class="my-2.5 px-1.5">
										{#each Object.keys(changelog[version][section]) as item}
											<div class="text-sm mb-2">
												<div class="font-semibold uppercase">
													{changelog[version][section][item].title}
												</div>
												<div class="mb-2 mt-1">{changelog[version][section][item].content}</div>
											</div>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>
		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
				on:click={() => {
					localStorage.version = $config.version;
					show = false;
				}}
				class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			>
				<span class="relative">Okay, Let's Go!</span>
			</button>
		</div>
	</div>
</Modal>
