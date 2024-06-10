<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { WEBUI_NAME, chatId, modelfiles, settings, showSettings, user } from '$lib/stores';

	import { slide, fade } from 'svelte/transition';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from './Navbar/Menu.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let selectedModels;

	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;
	let showDropdown = false;

</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />
<nav id="nav" class=" sticky py-2.5 top-0 flex flex-row justify-center z-30">
	<div class=" flex max-w-full w-full mx-auto px-5 pt-3 md:px-[1.3rem]">
		<div class="flex flex-wrap justify-between items-center w-full max-w-full">
			<button class="flex self-center" on:click={() => {
				initNewChat();
			}}>
				<img
					src="/logo-mbzuai.png"
					class="w-[108px]"
					alt="logo-mbzuai"
				/>
				<img
					src="/logo-ciai.png"
					class="ml-4 w-[70px]"
					alt="logo-ciai"
				/>
			</button>

			<div class="overflow-hidden ml-5 flex-1 text-xl font-semibold text-black dark:text-white">
				HR Assistant Chatbot
			</div>

			<div class="self-start flex flex-none items-center">
				<div class="md:hidden flex self-center w-[1px] h-5 mx-2 bg-gray-300 dark:bg-stone-700" />
				<div class="flex flex-col">
				{#if $user !== undefined}
					<button
						class=" flex rounded-xl py-3 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
						on:click={() => {
							showDropdown = !showDropdown;
						}}
					>
						<div class=" self-center mr-3">
							<img
								src="/user-ava.png"
								class=" max-w-[30px] object-cover rounded-full"
								alt="User profile"
							/>
						</div>
						<!-- <div class=" self-center font-semibold">{$user.name}</div> -->
					</button>

					{#if showDropdown}
						<div
							id="dropdownDots"
							class="absolute z-40 top-[80px] right-[20px] rounded-lg shadow w-[160px] bg-white dark:bg-gray-900"
							transition:fade|slide={{ duration: 100 }}
						>
							<div class="px-4 py-2 w-full">
								<ModelSelector bind:selectedModels showSetDefault={true} />
							</div>
							<hr class=" dark:border-gray-800 m-0 p-0" />

							<div class="p-1 py-2 w-full">
								<a
									class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
									href="/documents"
									on:click={() => {
										// selectedChatId = null;
										chatId.set('');
									}}
								>
								<div class="self-center ml-1 mr-3 dark:text-white">
									<svg width="14" height="14" viewBox="0 0 12 12" fill="none" stroke-width="1" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
										<path d="M10.7775 11.1525H1.22247C0.924105 11.1525 0.637956 11.034 0.426978 10.823C0.216 10.612 0.0974731 10.3259 0.0974731 10.0275V1.9875C0.0974731 1.68913 0.216 1.40298 0.426978 1.192C0.637956 0.981023 0.924105 0.862497 1.22247 0.862497H4.49997C4.66301 0.861411 4.82426 0.896499 4.97211 0.965235C5.11996 1.03397 5.25072 1.13464 5.35497 1.26L6.02247 2.01C6.0577 2.05087 6.1015 2.08348 6.15076 2.10552C6.20002 2.12755 6.25352 2.13847 6.30747 2.1375L10.755 2.0925C11.0547 2.09446 11.3416 2.21441 11.5536 2.42637C11.7656 2.63833 11.8855 2.92525 11.8875 3.225V9.975C11.8935 10.1256 11.8694 10.2759 11.8166 10.417C11.7638 10.5582 11.6833 10.6874 11.5799 10.797C11.4766 10.9067 11.3523 10.9946 11.2145 11.0557C11.0767 11.1167 10.9282 11.1496 10.7775 11.1525ZM1.22247 1.6125C1.12302 1.6125 1.02763 1.65201 0.957308 1.72233C0.886982 1.79266 0.847473 1.88804 0.847473 1.9875V10.0275C0.847473 10.127 0.886982 10.2223 0.957308 10.2927C1.02763 10.363 1.12302 10.4025 1.22247 10.4025H10.7775C10.8776 10.4025 10.9738 10.3632 11.0453 10.2931C11.1168 10.223 11.158 10.1276 11.16 10.0275V3.2775C11.16 3.17605 11.1197 3.07876 11.0479 3.00703C10.9762 2.9353 10.8789 2.895 10.7775 2.895L6.33747 2.94C6.17049 2.94479 6.00482 2.9091 5.85462 2.83596C5.70443 2.76282 5.57417 2.65441 5.47497 2.52L4.81497 1.77C4.7781 1.72131 4.7305 1.68177 4.67587 1.65446C4.62124 1.62714 4.56105 1.61278 4.49997 1.6125H1.22247Z" fill="#323333"/>
									</svg>
										
								</div>
									<div class=" self-center font-medium">{$i18n.t('Documents')}</div>
								</a>
							</div>
							<hr class=" dark:border-gray-800 m-0 p-0" />
							<div class="p-1 py-2 w-full">

								<button
									class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
									on:click={async () => {
										await showSettings.set(true);
										showDropdown = false;
									}}
								>
									<div class=" self-center mr-3">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="w-5 h-5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"
											/>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
											/>
										</svg>
									</div>
									<div class=" self-center font-medium">{$i18n.t('Settings')}</div>
								</button>
							</div>


							<hr class=" dark:border-gray-800 m-0 p-0" />

							<div class="p-1 py-2 w-full">
								<button
									class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
									on:click={() => {
										localStorage.removeItem('token');
										location.href = '/auth';
										showDropdown = false;
									}}
								>
									<div class=" self-center mr-3">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-5 h-5"
										>
											<path
												fill-rule="evenodd"
												d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
												clip-rule="evenodd"
											/>
											<path
												fill-rule="evenodd"
												d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
									<div class=" self-center font-medium">{$i18n.t('Sign Out')}</div>
								</button>
							</div>
						</div>
					{/if}
				{/if}
			</div>
		
				<!-- {#if !shareEnabled}
					<Tooltip content={$i18n.t('Settings')}>
						<button
							class="cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
							id="open-settings-button"
							on:click={async () => {
								await showSettings.set(!$showSettings);
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-5 h-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
								/>
							</svg>
						</button>
					</Tooltip>
				{:else}
					<Menu
						{chat}
						{shareEnabled}
						shareHandler={() => {
							showShareChatModal = !showShareChatModal;
						}}
						downloadHandler={() => {
							showDownloadChatModal = !showDownloadChatModal;
						}}
					>
						<button
							class="cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
						>
							<div class=" m-auto self-center">
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
										d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
									/>
								</svg>
							</div>
						</button>
					</Menu>
				{/if} -->
				<!-- <Tooltip content={$i18n.t('New Chat')}>
					<button
						id="new-chat-button"
						class=" cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
						on:click={() => {
							initNewChat();
						}}
					>
						<div class=" m-auto self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-5 h-5"
							>
								<path
									d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
								/>
								<path
									d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
								/>
							</svg>
						</div>
					</button>
				</Tooltip> -->
			</div>
		</div>
	</div>
</nav>
