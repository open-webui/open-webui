<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import InputMenu from '$lib/components/chat/MessageInput/InputMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import Headphone from '$lib/components/icons/Headphone.svelte';
	import NearAIIcon from '$lib/components/icons/NearAI.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { getContext } from 'svelte';
	import Fuse from 'fuse.js';
	import { allPrompts } from './data';
	import { arraysEqual } from './utils';
	import { goto, preloadCode } from '$app/navigation';

	const i18n: any = getContext('i18n');

	onMount(() => {
		preloadCode('/auth');
	});

	let inputValue = '';

	let filteredPrompts: any[] = [];
	const getFilteredPrompts = (inputValue: string) => {
		const sortedPrompts = [...(allPrompts ?? [])].sort(() => Math.random() - 0.5);
		if (inputValue.length > 500) {
			filteredPrompts = [];
		} else {
			const fuse = new Fuse(sortedPrompts, {
				keys: ['content', 'title'],
				threshold: 0.5
			});
			const newFilteredPrompts =
				inputValue.trim() && fuse
					? fuse.search(inputValue.trim()).map((result) => result.item)
					: sortedPrompts;

			if (!arraysEqual(filteredPrompts, newFilteredPrompts)) {
				filteredPrompts = newFilteredPrompts;
			}
		}
	};
	$: getFilteredPrompts(inputValue);

	const gotoAuth = async () => {
		await goto(`/auth`);
	};
</script>

<div
	class="h-screen max-h-[100dvh] text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 w-full max-w-full flex flex-col"
>
	<!-- model selector -->
	<div class="flex w-full items-center justify-between absolute top-0 left-0 p-4">
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<div class="flex items-center cursor-pointer">
					<NearAIIcon />
					<ChevronDown className="ml-3 size-4.5" />
				</div>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				class="w-full max-w-[400px] rounded-xl p-5 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
				sideOffset={10}
				alignOffset={10}
			>
				<div class="flex flex-col gap-y-3">
					<h5 class="font-semibold text-lg">Chat with private AI models for free.</h5>
					<p>Get access to your personal AI models without worrying leaking private information.</p>

					<button
						type="button"
						class="bg-gray-700/5 font-semibold hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition rounded-lg text-sm py-2.5 px-5"
						on:click={gotoAuth}
					>
						Sign In & Sign Up
					</button>
				</div>
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<button
			type="button"
			class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition rounded-lg font-semibold text-sm py-2.5 px-5"
			on:click={gotoAuth}
		>
			Sign In & Sign Up
		</button>
	</div>

	<div class="w-full h-full flex flex-col">
		<div class="m-auto w-full max-w-6xl px-2 2xl:px-20 translate-y-6 py-24 text-center">
			<div
				class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary"
			>
				<div class="w-full flex flex-col justify-center items-center">
					<!-- title -->
					<div
						class="flex flex-col justify-center gap-3 items-center sm:gap-3.5 w-fit px-5 max-w-2xl"
					>
						<h1 class="text-3xl sm:text-3xl flex items-center">NEAR AI</h1>
						<p class="text-base dark:text-gray-300">
							Chat with your personal assistant without worrying about leaking private information.
						</p>
					</div>
					<!-- input -->
					<div class="text-base font-normal md:max-w-3xl w-full py-3">
						<div class="w-full font-primary bg-white dark:bg-gray-900 px-2.5 mx-auto inset-x-0">
							<div
								class="flex-1 flex flex-col relative w-full shadow-lg rounded-3xl border border-gray-50 dark:border-gray-850 hover:border-gray-100 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800 transition px-1 bg-white/90 dark:bg-gray-400/5 dark:text-gray-100"
							>
								<div class="px-2.5">
									<div
										class="scrollbar-hidden rtl:text-right ltr:text-left bg-transparent dark:text-gray-100 outline-hidden w-full pt-2.5 pb-[5px] px-1 resize-none h-fit max-h-80 overflow-auto"
										id="chat-input-container"
									>
										<textarea
											class="scrollbar-hidden bg-transparent dark:text-gray-200 outline-hidden w-full pt-3 px-1 resize-none"
											placeholder={$i18n.t('How can I help you today?')}
											rows="1"
											bind:value={inputValue}
											on:keydown={async (e) => {
												const enterPressed = e.key === 'Enter' || e.keyCode === 13;
												if (enterPressed && inputValue) {
													gotoAuth();
												}
											}}
										/>
									</div>
									<div class=" flex justify-between mt-0.5 mb-2.5 mx-0.5 max-w-full" dir="ltr">
										<div class="ml-1 self-end flex items-center flex-1 max-w-[80%]">
											<InputMenu
												inputFilesHandler={() => {}}
												screenCaptureHandler={() => {}}
												uploadFilesHandler={() => {}}
												uploadGoogleDriveHandler={() => {}}
												uploadOneDriveHandler={() => {}}
												onClose={() => {}}
											>
												<div
													class="bg-transparent hover:bg-gray-100 text-gray-800 dark:text-white dark:hover:bg-gray-800 rounded-full p-1.5 outline-hidden focus:outline-hidden"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														aria-hidden="true"
														fill="currentColor"
														class="size-5"
													>
														<path
															d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
														/>
													</svg>
												</div>
											</InputMenu>
										</div>

										<div class="self-end flex space-x-1 mr-1 shrink-0">
											<!-- <Tooltip content={$i18n.t('Dictate')}>
												<button
													id="voice-input-button"
													class=" text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 mr-0.5 self-center"
													type="button"
													on:click={gotoAuth}
													aria-label="Voice Input"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-5 h-5 translate-y-[0.5px]"
													>
														<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
														<path
															d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"
														/>
													</svg>
												</button>
											</Tooltip> -->
											{#if inputValue === ''}
												<div class="flex items-center">
													<Tooltip content={$i18n.t('Voice mode')}>
														<button
															class="bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full p-1.5 self-center"
															type="button"
															on:click={gotoAuth}
															aria-label={$i18n.t('Voice mode')}
														>
															<Headphone className="size-5" />
														</button>
													</Tooltip>
												</div>
											{:else}
												<div class="flex items-center">
													<Tooltip content={$i18n.t('Send message')}>
														<button
															class="bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full p-1.5 self-center"
															type="button"
															on:click={gotoAuth}
															aria-label={$i18n.t('Send message')}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="size-5"
															>
																<path
																	fill-rule="evenodd"
																	d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
																	clip-rule="evenodd"
																/>
															</svg>
														</button>
													</Tooltip>
												</div>
											{/if}
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
					<!-- suggestion -->
					<div class="mx-auto max-w-2xl w-full font-primary mt-2">
						<div class="mx-5">
							<div
								class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-600 dark:text-gray-400"
							>
								<Bolt />
								{$i18n.t('Suggested')}
							</div>
							<div class="h-40 w-full">
								<div role="list" class="max-h-40 overflow-auto scrollbar-none items-start">
									{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
										<!-- svelte-ignore a11y-no-interactive-element-to-noninteractive-role -->
										<button
											role="listitem"
											class="waterfall flex flex-col flex-1 shrink-0 w-full justify-between
                                            px-3 py-2 rounded-xl bg-transparent hover:bg-black/5 text-base font-normal
                                            dark:hover:bg-white/5 transition group"
											style="animation-delay: {idx * 60}ms"
											on:click={() => {
												inputValue = prompt.content;
											}}
										>
											<div class="flex flex-col text-left">
												{#if prompt.title && prompt.title[0] !== ''}
													<div
														class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
													>
														{prompt.title[0]}
													</div>
													<div
														class="text-xs text-gray-600 dark:text-gray-400 font-normal line-clamp-1"
													>
														{prompt.title[1]}
													</div>
												{:else}
													<div
														class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
													>
														{prompt.content}
													</div>
													<div
														class="text-xs text-gray-600 dark:text-gray-400 font-normal line-clamp-1"
													>
														{$i18n.t('Prompt')}
													</div>
												{/if}
											</div>
										</button>
									{/each}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
