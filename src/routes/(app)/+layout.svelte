<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext } from 'svelte';
	import { openDB, deleteDB } from 'idb';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';

	import { getModels as _getModels } from '$lib/utils';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { getModelfiles } from '$lib/apis/modelfiles';
	import { getPrompts } from '$lib/apis/prompts';

	import { getDocs } from '$lib/apis/documents';
	import { getAllChatTags } from '$lib/apis/chats';

	import {
		user,
		showSettings,
		settings,
		models,
		modelfiles,
		prompts,
		documents,
		tags,
		showChangelog,
		config
	} from '$lib/stores';
	import { REQUIRED_OLLAMA_VERSION, WEBUI_API_BASE_URL } from '$lib/constants';
	import { compareVersion } from '$lib/utils';

	import SettingsModal from '$lib/components/chat/SettingsModal.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';
	let loaded = false;
	let showShortcutsButtonElement: HTMLButtonElement;
	let DB = null;
	let localDBChats = [];

	let showShortcuts = false;

	const getModels = async () => {
		return _getModels(localStorage.token);
	};

	const setOllamaVersion = async (version: string = '') => {
		if (version === '') {
			version = await getOllamaVersion(localStorage.token).catch((error) => {
				return '';
			});
		}

		ollamaVersion = version;

		console.log(ollamaVersion);
		if (compareVersion(REQUIRED_OLLAMA_VERSION, ollamaVersion)) {
			toast.error(`Ollama Version: ${ollamaVersion !== '' ? ollamaVersion : 'Not Detected'}`);
		}
	};

	onMount(async () => {
		if ($user === undefined) {
			await goto('/auth');
		} else if (['user', 'admin'].includes($user.role)) {
			try {
				// Check if IndexedDB exists
				DB = await openDB('Chats', 1);

				if (DB) {
					const chats = await DB.getAllFromIndex('chats', 'timestamp');
					localDBChats = chats.map((item, idx) => chats[chats.length - 1 - idx]);

					if (localDBChats.length === 0) {
						await deleteDB('Chats');
					}
				}

				console.log(DB);
			} catch (error) {
				// IndexedDB Not Found
			}

			await models.set(await getModels());
			await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));

			await modelfiles.set(await getModelfiles(localStorage.token));
			await prompts.set(await getPrompts(localStorage.token));
			await documents.set(await getDocs(localStorage.token));
			await tags.set(await getAllChatTags(localStorage.token));

			modelfiles.subscribe(async () => {
				// should fetch models
				await models.set(await getModels());
			});

			document.addEventListener('keydown', function (event) {
				const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
				// Check if the Shift key is pressed
				const isShiftPressed = event.shiftKey;

				// Check if Ctrl + Shift + O is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'o') {
					event.preventDefault();
					console.log('newChat');
					document.getElementById('sidebar-new-chat-button')?.click();
				}

				// Check if Shift + Esc is pressed
				if (isShiftPressed && event.key === 'Escape') {
					event.preventDefault();
					console.log('focusInput');
					document.getElementById('chat-textarea')?.focus();
				}

				// Check if Ctrl + Shift + ; is pressed
				if (isCtrlPressed && isShiftPressed && event.key === ';') {
					event.preventDefault();
					console.log('copyLastCodeBlock');
					const button = [...document.getElementsByClassName('copy-code-button')]?.at(-1);
					button?.click();
				}

				// Check if Ctrl + Shift + C is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'c') {
					event.preventDefault();
					console.log('copyLastResponse');
					const button = [...document.getElementsByClassName('copy-response-button')]?.at(-1);
					console.log(button);
					button?.click();
				}

				// Check if Ctrl + Shift + S is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 's') {
					event.preventDefault();
					console.log('toggleSidebar');
					document.getElementById('sidebar-toggle-button')?.click();
				}

				// Check if Ctrl + Shift + Backspace is pressed
				if (isCtrlPressed && isShiftPressed && event.key === 'Backspace') {
					event.preventDefault();
					console.log('deleteChat');
					document.getElementById('delete-chat-button')?.click();
				}

				// Check if Ctrl + . is pressed
				if (isCtrlPressed && event.key === '.') {
					event.preventDefault();
					console.log('openSettings');
					showSettings.set(!$showSettings);
				}

				// Check if Ctrl + / is pressed
				if (isCtrlPressed && event.key === '/') {
					event.preventDefault();
					console.log('showShortcuts');
					showShortcutsButtonElement.click();
				}
			});

			if ($user.role === 'admin') {
				showChangelog.set(localStorage.version !== $config.version);
			}

			await tick();
		}

		loaded = true;
	});
</script>

<div class=" hidden lg:flex fixed bottom-0 right-0 px-3 py-3 z-10">
	<Tooltip content="Help" placement="left">
		<button
			id="show-shortcuts-button"
			bind:this={showShortcutsButtonElement}
			class="text-gray-600 dark:text-gray-300 bg-gray-300/20 w-6 h-6 flex items-center justify-center text-xs rounded-full"
			on:click={() => {
				showShortcuts = !showShortcuts;
			}}
		>
			?
		</button>
	</Tooltip>
</div>

<ShortcutsModal bind:show={showShortcuts} />
<SettingsModal bind:show={$showSettings} />
<ChangelogModal show={false} />

<div class="app relative">
	<svg class="z-0 absolute top-0 left-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice"><defs><radialGradient id="Gradient1" cx="50%" cy="50%" fx="0.441602%" fy="50%" r=".5"><animate attributeName="fx" dur="34s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(95, 120, 234, 1)"></stop><stop offset="100%" stop-color="rgba(95, 120, 234, 0)"></stop></radialGradient><radialGradient id="Gradient2" cx="50%" cy="50%" fx="2.68147%" fy="50%" r=".5"><animate attributeName="fx" dur="23.5s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(14, 139, 254, 1)"></stop><stop offset="100%" stop-color="rgba(14, 139, 254, 0)"></stop></radialGradient><radialGradient id="Gradient3" cx="50%" cy="50%" fx="0.836536%" fy="50%" r=".5"><animate attributeName="fx" dur="21.5s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(27, 232, 217, 1)"></stop><stop offset="100%" stop-color="rgba(27, 232, 217, 0)"></stop></radialGradient></defs><rect x="13.744%" y="1.18473%" width="100%" height="100%" fill="url(#Gradient1)" transform="rotate(334.41 50 50)"><animate attributeName="x" dur="20s" values="25%;0%;25%" repeatCount="indefinite"></animate><animate attributeName="y" dur="21s" values="0%;25%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="7s" repeatCount="indefinite"></animateTransform></rect><rect x="-2.17916%" y="35.4267%" width="100%" height="100%" fill="url(#Gradient2)" transform="rotate(255.072 50 50)"><animate attributeName="x" dur="23s" values="-25%;0%;-25%" repeatCount="indefinite"></animate><animate attributeName="y" dur="24s" values="0%;50%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="12s" repeatCount="indefinite"></animateTransform></rect><rect x="9.00483%" y="14.5733%" width="100%" height="100%" fill="url(#Gradient3)" transform="rotate(139.903 50 50)"><animate attributeName="x" dur="25s" values="0%;25%;0%" repeatCount="indefinite"></animate><animate attributeName="y" dur="12s" values="0%;25%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="360 50 50" to="0 50 50" dur="9s" repeatCount="indefinite"></animateTransform></rect></svg>
	<div
		class=" text-gray-700 dark:text-gray-100 bg-[#ffffff80] dark:bg-gray-900 backdrop-blur-xl min-h-screen overflow-auto flex flex-row"
	>
		{#if loaded}
			{#if !['user', 'admin'].includes($user.role)}
				<div class="fixed w-full h-full flex z-50">
					<div
						class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
					>
						<div class="m-auto pb-44 flex flex-col justify-center">
							<div class="max-w-md">
								<div class="text-center dark:text-white text-2xl font-medium z-50">
									Account Activation Pending<br /> Contact Admin for WebUI Access
								</div>

								<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
									Your account status is currently pending activation. To access the WebUI, please
									reach out to the administrator. Admins can manage user statuses from the Admin
									Panel.
								</div>

								<div class=" mt-6 mx-auto relative group w-fit">
									<button
										class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 text-gray-700 transition font-medium text-sm"
										on:click={async () => {
											location.href = '/';
										}}
									>
										{$i18n.t('Check Again')}
									</button>

									<button
										class="text-xs text-center w-full mt-2 text-gray-400 underline"
										on:click={async () => {
											localStorage.removeItem('token');
											location.href = '/auth';
										}}>{$i18n.t('Sign Out')}</button
									>
								</div>
							</div>
						</div>
					</div>
				</div>
			{:else if localDBChats.length > 0}
				<div class="fixed w-full h-full flex z-50">
					<div
						class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
					>
						<div class="m-auto pb-44 flex flex-col justify-center">
							<div class="max-w-md">
								<div class="text-center dark:text-white text-2xl font-medium z-50">
									Important Update<br /> Action Required for Chat Log Storage
								</div>

								<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
									{$i18n.t(
										"Saving chat logs directly to your browser's storage is no longer supported. Please take a moment to download and delete your chat logs by clicking the button below. Don't worry, you can easily re-import your chat logs to the backend through"
									)}
									<span class="font-semibold dark:text-white"
										>{$i18n.t('Settings')} > {$i18n.t('Chats')} > {$i18n.t('Import Chats')}</span
									>. {$i18n.t(
										'This ensures that your valuable conversations are securely saved to your backend database. Thank you!'
									)}
								</div>

								<div class=" mt-6 mx-auto relative group w-fit">
									<button
										class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 transition font-medium text-sm"
										on:click={async () => {
											let blob = new Blob([JSON.stringify(localDBChats)], {
												type: 'application/json'
											});
											saveAs(blob, `chat-export-${Date.now()}.json`);

											const tx = DB.transaction('chats', 'readwrite');
											await Promise.all([tx.store.clear(), tx.done]);
											await deleteDB('Chats');

											localDBChats = [];
										}}
									>
										Download & Delete
									</button>

									<button
										class="text-xs text-center w-full mt-2 text-gray-400 underline"
										on:click={async () => {
											localDBChats = [];
										}}>{$i18n.t('Close')}</button
									>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<Sidebar />
			<slot />
		{/if}
	</div>
</div>

<style>
	.loading {
		display: inline-block;
		clip-path: inset(0 1ch 0 0);
		animation: l 1s steps(3) infinite;
		letter-spacing: -0.5px;
	}

	@keyframes l {
		to {
			clip-path: inset(0 -1ch 0 0);
		}
	}

	pre[class*='language-'] {
		position: relative;
		overflow: auto;

		/* make space  */
		margin: 5px 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 10px;
	}

	pre[class*='language-'] button {
		position: absolute;
		top: 5px;
		right: 5px;

		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;

		border: ridge 1px #7b7b7c;
		border-radius: 5px;
		text-shadow: #c4c4c4 0 0 2px;
	}

	pre[class*='language-'] button:hover {
		cursor: pointer;
		background-color: #bcbabb;
	}
</style>
