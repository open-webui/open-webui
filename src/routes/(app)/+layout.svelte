<script lang="ts">
	const LAYOUT_VERSION = 'v3-chat-events-' + Date.now(); // Unique version identifier
	console.log(`%%%%%%% +layout.svelte SCRIPT TOP LEVEL EXECUTING - VERSION: ${LAYOUT_VERSION} %%%%%%%`);
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
	import type { LocalMcpoToolConfig } from '$lib/types/tools'; // Import LocalMcpoToolConfig
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

	// Define a variable to hold the current handler function.
	// Its content will be updated by onMount/HMR, but chatEventListenerWrapper's reference remains stable.
	let currentActualHandler = async (eventData: any, cb?: any) => {
		console.warn('%%%%%%% execute:tool event received, but currentActualHandler not yet initialized by onMount. Event Data:', eventData, '%%%%%%%');
		// This basic version of currentActualHandler should ideally not be called if onMount runs correctly first.
	};

	// This wrapper function's reference remains stable across HMR updates of the Svelte component.
	// Socket.io listeners will be bound to this stable reference.
	const chatEventListenerWrapper = (event: any, cb: any) => {
		// Check if this is an execute:tool event for local MCPO
		if (event?.data?.type === 'execute:tool' && event?.data?.data?.server?.url?.startsWith('http://localhost:8000')) {
			console.log(`%%%%%%% APP LAYOUT: Intercepting local MCPO execute:tool from chat-events %%%%%%%`, event.data.data);
			// Delegate to our handler for local MCPO tools
			currentActualHandler(event.data.data, cb);
		}
		// Let other chat events pass through without handling
	};
	
	// This is the function that will contain the actual logic.
	// It will be reassigned inside onMount to ensure it's the latest version from the module.
	const assignNewHandleExecuteToolEvent = () => {
		currentActualHandler = async (eventData: {
			id: string; 
			name: string; 
			params: Record<string, any>; 
			server?: { url: string; [key: string]: any }; 
			chat_id?: string; 
			message_id?: string; 
			session_id?: string;
			[key: string]: any; 
		}, cb?: any) => {
			console.log(`%%%%%%% APP LAYOUT handleExecuteToolEvent CALLED! VERSION: ${LAYOUT_VERSION} %%%%%%%`, eventData);

			const operationName = eventData.name;
			const toolArgs = eventData.params;
			const callEventId = eventData.id; 
			const chatId = eventData.chat_id; 
			const messageId = eventData.message_id; 

			toast.info(`Executing local tool: ${operationName} via wrapper.`);
			console.log('Current $localMcpoTools store content (via wrapper):', get(localMcpoToolsStore));

			const localTools = get(localMcpoToolsStore);
			let targetToolServerConfig: LocalMcpoToolConfig | undefined = undefined;

			for (const serverCfg of localTools) {
				if (serverCfg.spec && serverCfg.spec.paths) {
					for (const pathRoute in serverCfg.spec.paths) {
						const pathItem = serverCfg.spec.paths[pathRoute];
						if (typeof pathItem === 'object' && pathItem !== null) {
							for (const httpMethod in pathItem) {
								const operation = pathItem[httpMethod];
								if (typeof operation === 'object' && operation !== null && operation.operationId === operationName) {
									targetToolServerConfig = serverCfg;
									break; 
								}
							}
						}
						if (targetToolServerConfig) break; 
					}
				}
				if (targetToolServerConfig) break; 
			}
			
			console.log(`Wrapped executeTool: Searching for server hosting operation "${operationName}". Found targetToolServerConfig:`, targetToolServerConfig);

			if (targetToolServerConfig) {
				if (!targetToolServerConfig.enabled) {
					const errorMsg = `Local MCPO Server "${targetToolServerConfig.name}" (hosting operation "${operationName}") is disabled by the user.`;
					console.warn(errorMsg);
					toast.warning(errorMsg);
					if (chatId && messageId) {
						localToolResultStore.set({
							toolId: callEventId,
							chatId: chatId,
							assistantMessageId: messageId,
							result: { success: false, error: errorMsg }
						});
					}
					return;
				}

				console.log(`Wrapped: Attempting to call executeLocalMcpoTool for operation "${operationName}" on server "${targetToolServerConfig.name}" with args:`, toolArgs);
				const result = await executeLocalMcpoTool(targetToolServerConfig, operationName, toolArgs);
				
				if (chatId && messageId) {
					localToolResultStore.set({
						toolId: callEventId,
						chatId: chatId,
						assistantMessageId: messageId,
						result: result
					});
				} else {
					console.warn('Wrapped: chat_id or message_id missing in execute:tool event, cannot set localToolResultStore for UI update.', eventData);
				}
				
				// Call the callback if provided (for chat-events handler)
				if (cb && typeof cb === 'function') {
					console.log(`%%%%%%% APP LAYOUT: Calling callback with result %%%%%%%`, result);
					cb(result);
				}
			} else {
				const errorMsg = `Wrapped: Local MCPO server config not found for operation "${operationName}". The operation is not defined in any discovered server's OpenAPI spec, or the hosting server is not enabled/discovered.`;
				console.warn(errorMsg, eventData);
				toast.error(errorMsg);
				if (chatId && messageId) {
					localToolResultStore.set({
						toolId: callEventId,
						chatId: chatId,
						assistantMessageId: messageId,
						result: { success: false, error: errorMsg }
					});
				}
				
				// Call the callback with error if provided
				if (cb && typeof cb === 'function') {
					console.log(`%%%%%%% APP LAYOUT: Calling callback with error %%%%%%%`, errorMsg);
					cb({ success: false, error: errorMsg });
				}
			}
		};
		console.log('%%%%%%% LAYOUT.SVELTE: currentActualHandler has been updated to the new version (full logic). %%%%%%%');
	};


	let unsubscribeSocketListener: (() => void) | null = null;
	let lastBoundSocketId: string | null = null; // Keep track of the socket we bound the wrapper to

	onMount(() => {
		console.log('%%%%%%% LAYOUT.SVELTE: onMount executing. %%%%%%%');
		assignNewHandleExecuteToolEvent(); // Ensure currentActualHandler points to the latest logic

		unsubscribeSocketListener = socketStore.subscribe(currentSocket => {
			const socketIdForLog = currentSocket && typeof currentSocket.id !== 'undefined' ? currentSocket.id : 'undefined_or_no_id';
			console.log(`%%%%%%% LAYOUT.SVELTE: socketStore.subscribe. currentSocket ID: ${socketIdForLog} %%%%%%%`);
		
			// Cleanup logic for a previously bound socket ID can be complex here due to HMR and store updates.
			// The onDestroy (onMount's return function) is the primary place for cleaning up the last known socket.
			// This subscription block mainly focuses on setting up the listener for the *current* socket from the store.

			if (currentSocket && 
				typeof currentSocket.on === 'function' && 
				typeof currentSocket.off === 'function' && 
				currentSocket.connected) { // Check for connected status
				
				const socketId = currentSocket.id || 'unknown';
				console.log(`%%%%%%% LAYOUT.SVELTE: Valid connected socket instance ${socketId}. Proceeding with listener setup. %%%%%%%`);
				
				// Remove any existing chat-events listeners to prevent duplicates
				console.log(`%%%%%%% LAYOUT.SVELTE: Removing any existing 'chat-events' listeners from socket ${socketId}. %%%%%%%`);
				currentSocket.off('chat-events', chatEventListenerWrapper);
				
				// Now add our listener for chat-events
				console.log(`%%%%%%% LAYOUT.SVELTE: Binding 'chat-events' to STABLE WRAPPER for socket ${socketId}. %%%%%%%`);
				currentSocket.on('chat-events', chatEventListenerWrapper);
				lastBoundSocketId = socketId; // Track the ID of the socket we just bound to
				
				console.log(`%%%%%%% LAYOUT.SVELTE: Wrapped chat-events listener attached to socket ${socketId}. %%%%%%%`);
				
				// Debug: Check how many listeners are attached
				if (typeof currentSocket.listenerCount === 'function') {
					console.log(`%%%%%%% DEBUG: Socket ${socketId} has ${currentSocket.listenerCount('chat-events')} 'chat-events' listeners %%%%%%%`);
				}

				// Define disconnect handler specific to this currentSocket instance
				const handleDisconnect = () => {
					console.log(`%%%%%%% LAYOUT.SVELTE: Socket ${currentSocket.id} disconnected. Removing wrapped listener. %%%%%%%`);
					// currentSocket here refers to the one from the outer scope of this handleDisconnect definition
					if (currentSocket && typeof currentSocket.off === 'function') {
						currentSocket.off('chat-events', chatEventListenerWrapper);
					}
					// If the disconnected socket is the one we were tracking, clear lastBoundSocketId
					if (lastBoundSocketId === currentSocket.id) {
						lastBoundSocketId = null;
					}
				};
				
				// Clean up any old disconnect listener for this event name before adding a new one for this specific socket instance
				currentSocket.off('disconnect', handleDisconnect); // This might not work if handleDisconnect reference changes; better to manage by a flag or a single named handler if issues persist
				currentSocket.on('disconnect', handleDisconnect);

			} else {
				console.log(`%%%%%%% LAYOUT.SVELTE: Socket not ready for listener attachment. Current socket:`, currentSocket, `%%%%%%%`);
				
				// If socket exists but not connected, set up a one-time listener for when it connects
				if (currentSocket && typeof currentSocket.on === 'function' && !currentSocket.connected) {
					console.log(`%%%%%%% LAYOUT.SVELTE: Socket exists but not connected. Setting up one-time connect listener. %%%%%%%`);
					
					const onConnect = () => {
						const socketId = currentSocket.id || 'unknown';
						console.log(`%%%%%%% LAYOUT.SVELTE: Socket ${socketId} connected! Setting up chat-events listener. %%%%%%%`);
						
						// Remove any existing listeners first
						currentSocket.off('chat-events', chatEventListenerWrapper);
						
						// Add our listener
						currentSocket.on('chat-events', chatEventListenerWrapper);
						lastBoundSocketId = socketId;
						
						console.log(`%%%%%%% LAYOUT.SVELTE: chat-events listener attached after connect for socket ${socketId}. %%%%%%%`);
						
						// Debug: Check how many listeners are attached
						if (typeof currentSocket.listenerCount === 'function') {
							console.log(`%%%%%%% DEBUG: Socket ${socketId} has ${currentSocket.listenerCount('chat-events')} 'chat-events' listeners %%%%%%%`);
						}
					};
					
					// Use once to ensure this only fires once
					currentSocket.once('connect', onConnect);
				}
				
				if (currentSocket === null && lastBoundSocketId !== null) {
					console.log(`%%%%%%% LAYOUT.SVELTE: Socket store emitted null, but we were previously bound to ${lastBoundSocketId}. %%%%%%%`);
				} else if (currentSocket === null) {
					lastBoundSocketId = null;
				}
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
				console.log('%%%%%%% LAYOUT.SVELTE: Component unmounting. Attempting to remove listener from socket:', lastBoundSocketId, '%%%%%%%');
				// Try to get the socket instance again, as it might have changed or the store re-emitted.
				const socketOnUnmount = get(socketStore);
				if (socketOnUnmount) {
					socketOnUnmount.off('chat-events', chatEventListenerWrapper);
				} else if (lastBoundSocketId) {
					// This is a best-effort if the socketStore is already null but we remember binding to a socket.
					// However, we don't have the instance to call .off() on.
					console.warn(`%%%%%%% LAYOUT.SVELTE: Cannot .off() on unmount as socketStore is null, though last bound to ${lastBoundSocketId}. %%%%%%%`);
				}
				lastBoundSocketId = null;
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
