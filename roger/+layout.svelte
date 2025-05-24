<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext } from 'svelte';
	import { openDB, deleteDB, type IDBPDatabase, type IDBPTransaction, type IDBPObjectStore, type DBSchema } from 'idb'; // Added DBSchema
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	import mermaid from 'mermaid';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fade } from 'svelte/transition';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getFunctions } from '$lib/apis/functions';
	import { getModels, getToolServersData, getVersionUpdates } from '$lib/apis';
	import { getAllTags } from '$lib/apis/chats';
	import { getPrompts } from '$lib/apis/prompts';
	import { getTools } from '$lib/apis/tools';
	import { getBanners } from '$lib/apis/configs';
	import { getUserSettings } from '$lib/apis/users';

	import { WEBUI_VERSION } from '$lib/constants';
	import { compareVersion } from '$lib/utils';

	import {
		config,
		user,
		settings,
		models,
		prompts,
		knowledge,
		tools,
		functions,
		tags,
		banners,
		showSettings,
		showChangelog,
		temporaryChatEnabled,
		toolServers
	} from '$lib/stores';

	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import SettingsModal from '$lib/components/chat/SettingsModal.svelte';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
	import UpdateInfoToast from '$lib/components/layout/UpdateInfoToast.svelte';
	import { get, derived } from 'svelte/store';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import LocalMcpoInitializer from '$lib/components/layout/LocalMcpoInitializer.svelte';
	import { localMcpoTools as localMcpoToolsStore, socket as socketStore, localToolResultStore } from '$lib/stores'; // Added localToolResultStore
	import type { Writable } from 'svelte/store';
	import { executeLocalMcpoTool } from '$lib/utils/localMcpoToolExecutor'; // Import the executor

	const i18n = getContext('i18n') as Writable<any>;

	// Define a schema for the 'Chats' database
	interface ChatsDBSchema extends DBSchema {
		chats: {
			key: string; // Assuming chat ID is the key
			value: any; // Replace 'any' with a proper Chat type if available
			indexes: { timestamp: number };
		};
	}

	let loaded = false;
	let DB: IDBPDatabase<ChatsDBSchema> | null = null; // Use the schema
	let localDBChats: any[] = [];
	let version: { current: string; latest: string } | any = null; // More specific type for version

	// Handler for execute:tool WebSocket event
	const handleExecuteToolEvent = async (data: { tool_id: string; tool_args: any; chat_id: string; message_id: string }) => {
		console.log('Received execute:tool event from backend for local tool:', data);
		toast.info(`Executing local tool: ${data.tool_id}`);

		// Log the current state of localMcpoToolsStore
		console.log('Current $localMcpoTools store content:', get(localMcpoToolsStore));

		// Find the tool configuration
		const localTools = get(localMcpoToolsStore);
		const toolConfig = localTools.find(t => t.name === data.name); // Use data.name for lookup

		console.log('executeTool: event data:', data, 'Found toolConfig:', toolConfig); // Updated log

		if (toolConfig) {
			if (!toolConfig.enabled) {
				const errorMsg = `Local tool "${data.tool_id}" is disabled by the user.`;
				console.warn(errorMsg);
				toast.warning(errorMsg);
				localToolResultStore.set({
					toolId: data.tool_id,
					chatId: data.chat_id,
					assistantMessageId: data.message_id,
					result: { success: false, error: errorMsg }
				});
				return;
			}

			console.log('Attempting to call executeLocalMcpoTool with payload:', data);
			const result = await executeLocalMcpoTool(data.tool_id, data.tool_args);
			localToolResultStore.set({
				toolId: data.tool_id,
				chatId: data.chat_id,
				assistantMessageId: data.message_id,
				result: result
			});
		} else {
			const errorMsg = `Received execute:tool event for "${data.tool_id}", but it's not a recognized local MCPO tool.`;
			console.warn(errorMsg);
			// Optionally inform Chat.svelte about this if needed, or just log
			// For now, we only set the store if it's a known local tool attempt.
			// If the backend sends execute:tool for non-local tools by mistake, this will catch it.
		}
	};

	let unsubscribeSocketListener: (() => void) | null = null;

	onMount(() => {
		// Setup WebSocket listener
		unsubscribeSocketListener = socketStore.subscribe(currentSocket => {
			if (currentSocket) {
				console.log('layout.svelte: Socket connected, attaching execute:tool listener.');
				currentSocket.on('execute:tool', handleExecuteToolEvent);
				currentSocket.on('disconnect', () => {
					console.log('layout.svelte: Socket disconnected, removing execute:tool listener from this socket instance.');
					currentSocket.off('execute:tool', handleExecuteToolEvent);
				});
			}
		});

		// IIFE for async operations originally in onMount
		(async () => {
			if ($user === undefined || $user === null) {
				await goto('/auth');
			} else if (['user', 'admin'].includes($user?.role)) {
				try {
					DB = await openDB<ChatsDBSchema>('Chats', 1); // Use the schema with openDB
					if (DB) {
						const chatsFromDB = await DB.getAllFromIndex('chats', 'timestamp');
						localDBChats = chatsFromDB.map((item: any, idx: number) => chatsFromDB[chatsFromDB.length - 1 - idx]);
						if (localDBChats.length === 0) {
							await deleteDB('Chats');
						}
					}
					console.log(DB);
				} catch (error) {
					// IndexedDB Not Found
				}

				const userSettings = await getUserSettings(localStorage.token).catch((error) => {
					console.error(error);
					return null;
				});

				if (userSettings) {
					settings.set(userSettings.ui);
				} else {
					let localStorageSettings = {} as Parameters<(typeof settings)['set']>[0];
					try {
						localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
					} catch (e: unknown) {
						console.error('Failed to parse settings from localStorage', e);
					}
					settings.set(localStorageSettings);
				}

				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);

				banners.set(await getBanners(localStorage.token));
				tools.set(await getTools(localStorage.token));
				// @ts-ignore Pre-existing type mismatch for getToolServersData or $settings.toolServers
				toolServers.set(await getToolServersData($i18n, $settings?.toolServers ?? []));


				document.addEventListener('keydown', async function (event) {
					const isCtrlPressed = event.ctrlKey || event.metaKey;
					const isShiftPressed = event.shiftKey;

					if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'o') {
						event.preventDefault();
						(document.getElementById('sidebar-new-chat-button') as HTMLElement)?.click();
					}
					if (isShiftPressed && event.key === 'Escape') {
						event.preventDefault();
						(document.getElementById('chat-input') as HTMLElement)?.focus();
					}
					if (isCtrlPressed && isShiftPressed && event.key === ';') {
						event.preventDefault();
						const button = [...document.getElementsByClassName('copy-code-button')]?.at(-1);
						(button as HTMLElement)?.click();
					}
					if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'c') {
						event.preventDefault();
						const button = [...document.getElementsByClassName('copy-response-button')]?.at(-1);
						(button as HTMLElement)?.click();
					}
					if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 's') {
						event.preventDefault();
						(document.getElementById('sidebar-toggle-button') as HTMLElement)?.click();
					}
					if (isCtrlPressed && isShiftPressed && (event.key === 'Backspace' || event.key === 'Delete')) {
						event.preventDefault();
						(document.getElementById('delete-chat-button') as HTMLElement)?.click();
					}
					if (isCtrlPressed && event.key === '.') {
						event.preventDefault();
						showSettings.set(!$showSettings);
					}
					if (isCtrlPressed && event.key === '/') {
						event.preventDefault();
						(document.getElementById('show-shortcuts-button') as HTMLElement)?.click();
					}
					if (isCtrlPressed && isShiftPressed && (event.key.toLowerCase() === `'` || event.key.toLowerCase() === `"`)) {
						event.preventDefault();
						temporaryChatEnabled.set(!$temporaryChatEnabled);
						await goto('/');
						const newChatButton = document.getElementById('new-chat-button');
						setTimeout(() => {
							(newChatButton as HTMLElement)?.click();
						}, 0);
					}
				});

				if ($user?.role === 'admin' && ($settings?.showChangelog ?? true)) {
					// @ts-ignore Pre-existing potentially spurious TS error on this line's expression
					showChangelog.set($settings?.version !== $config?.version);
				}

				if ($user?.permissions?.chat?.temporary ?? true) {
					if ($page.url.searchParams.get('temporary-chat') === 'true') {
						temporaryChatEnabled.set(true);
					}
					if ($user?.permissions?.chat?.temporary_enforced) {
						temporaryChatEnabled.set(true);
					}
				}

				if ($user?.role === 'admin') {
					if (localStorage.dismissedUpdateToast) {
						const dismissedUpdateToastTime = Number(localStorage.dismissedUpdateToast);
						const dismissedDate = new Date(dismissedUpdateToastTime);
						const now = new Date();
						if (now.getTime() - dismissedDate.getTime() > 24 * 60 * 60 * 1000) {
							checkForVersionUpdates();
						}
					} else {
						checkForVersionUpdates();
					}
				}
				await tick();
			}
			loaded = true;
		})(); // End of IIFE

		// Return cleanup function for onMount
		return () => {
			if (unsubscribeSocketListener) {
				unsubscribeSocketListener();
			}
			const currentSocket = get(socketStore);
			if (currentSocket) {
				console.log('layout.svelte: Component unmounting, removing execute:tool listener.');
				currentSocket.off('execute:tool', handleExecuteToolEvent);
			}
		};
	});

	const checkForVersionUpdates = async () => {
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});
	};
</script>

<SettingsModal bind:show={$showSettings} />
<ChangelogModal bind:show={$showChangelog} />

{#if version && compareVersion(version.latest, version.current) && ($settings?.showUpdateToast ?? true)}
	<div class=" absolute bottom-8 right-8 z-50" in:fade={{ duration: 100 }}>
		<UpdateInfoToast
			{version}
			on:close={() => {
				localStorage.setItem('dismissedUpdateToast', Date.now().toString());
				version = null;
			}}
		/>
	</div>
{/if}

<div class="app relative">
	<div
		class=" text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
	>
		{#if !['user', 'admin'].includes($user?.role)}
			<AccountPending />
		{:else if localDBChats.length > 0}
			<div class="fixed w-full h-full flex z-50">
				<div
					class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
				>
					<div class="m-auto pb-44 flex flex-col justify-center">
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

										if (DB) {
											const tx = DB.transaction('chats', 'readwrite'); // Revert to inferred type
											const store = tx.store; // Revert to inferred type
											await Promise.all([store.clear(), tx.done]);
											await deleteDB('Chats');
										}
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
			<!-- Removed extra closing div here -->
		{/if}

		<Sidebar />

		{#if loaded}
			<slot />
		{:else}
	<div class="w-full flex-1 h-full flex items-center justify-center">
		<Spinner />
	</div>
{/if}

<LocalMcpoInitializer />

</div> <!-- This closes the div with class "text-gray-700 ..." -->
</div> <!-- This closes the div with class "app relative" -->

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
