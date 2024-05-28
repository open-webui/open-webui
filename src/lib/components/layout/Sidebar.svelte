<script lang="ts">
	import { goto } from '$app/navigation';
	import { user, chats, settings, showSettings, chatId, tags, showSidebar, documents } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import {
		deleteChatById,
		getChatList,
		getChatById,
		getChatListByTagName,
		updateChatById,
		getAllChatTags,
		archiveChatById
	} from '$lib/apis/chats';
	import {
		uploadDocToVectorDB
	} from '$lib/apis/rag';
	import { createNewDoc, getDocs } from '$lib/apis/documents';
	import { transcribeAudio } from '$lib/apis/audio';
	import { toast } from 'svelte-sonner';
	import { fade, slide } from 'svelte/transition';
	import { SUPPORTED_FILE_TYPE, SUPPORTED_FILE_EXTENSIONS, WEBUI_BASE_URL } from '$lib/constants';
	import { transformFileName } from '$lib/utils';
	
	import Tooltip from '../common/Tooltip.svelte';
	import ChatMenu from './Sidebar/ChatMenu.svelte';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ArchiveBox from '../icons/ArchiveBox.svelte';
	import ArchivedChatsModal from './Sidebar/ArchivedChatsModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	const BREAKPOINT = 1024;


	export let shareEnabled: boolean = false;
	export let selectedModels;

	let show = false;
	let navElement;

	let title: string = 'UI';
	let search = '';

	let shareChatId = null;

	let selectedChatId = null;

	let chatDeleteId = null;
	let chatTitleEditId = null;
	let chatTitle = '';

	let showArchivedChatsModal = false;
	let showShareChatModal = false;
	let showDropdown = false;
	let isEditing = false;
	let showMoreDoc = false;

	// upload files
	let filesInputElement;
	let inputFiles;


	let arrowClass = ''
	let documentsMock = [
		{
			collection_name: 'collection_name',
			filename: 'filename',
			name: 'name',
			title: 'title'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		{
			collection_name: 'collection_name1',
			filename: 'filename1',
			name: 'name1',
			title: 'title1'
		},
		]
	let filteredDocs;
	$: filteredDocs = showMoreDoc ? $documents : $documents.slice(0,5)

	onMount(async () => {
		// showSidebar.set(window.innerWidth > BREAKPOINT);

		// customization: hide sidebar by default
		showSidebar.set(false)
		await chats.set(await getChatList(localStorage.token));

		let touchstart;
		let touchend;

		function checkDirection() {
			const screenWidth = window.innerWidth;
			const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
			if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
				if (touchend.screenX < touchstart.screenX) {
					showSidebar.set(false);
				}
				if (touchend.screenX > touchstart.screenX) {
					showSidebar.set(true);
				}
			}
		}

		const onTouchStart = (e) => {
			touchstart = e.changedTouches[0];
			console.log(touchstart.clientX);
		};

		const onTouchEnd = (e) => {
			touchend = e.changedTouches[0];
			checkDirection();
		};

		const onResize = () => {
			if ($showSidebar && window.innerWidth < BREAKPOINT) {
				showSidebar.set(false);
			}
		};

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);
		window.addEventListener('resize', onResize);

		return () => {
			window.removeEventListener('touchstart', onTouchStart);
			window.removeEventListener('touchend', onTouchEnd);
			window.removeEventListener('resize', onResize);
		};
	});

	// Helper function to fetch and add chat content to each chat
	const enrichChatsWithContent = async (chatList) => {
		const enrichedChats = await Promise.all(
			chatList.map(async (chat) => {
				const chatDetails = await getChatById(localStorage.token, chat.id).catch((error) => null); // Handle error or non-existent chat gracefully
				if (chatDetails) {
					chat.chat = chatDetails.chat; // Assuming chatDetails.chat contains the chat content
				}
				return chat;
			})
		);

		await chats.set(enrichedChats);
	};

	const loadChat = async (id) => {
		goto(`/c/${id}`);
	};

	const editChatTitle = async (id, _title) => {
		if (_title === '') {
			toast.error('Title cannot be an empty string.');
		} else {
			title = _title;

			await updateChatById(localStorage.token, id, {
				title: _title
			});
			await chats.set(await getChatList(localStorage.token));
		}
	};

	const deleteChat = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(error);
			chatDeleteId = null;

			return null;
		});

		if (res) {
			if ($chatId === id) {
				goto('/');
			}

			await chats.set(await getChatList(localStorage.token));
		}
	};

	const saveSettings = async (updated) => {
		await settings.set({ ...$settings, ...updated });
		localStorage.setItem('settings', JSON.stringify($settings));
		location.href = '/';
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		await chats.set(await getChatList(localStorage.token));
	};

	const uploadDoc = async (file) => {
		const res = await uploadDocToVectorDB(localStorage.token, '', file).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			await createNewDoc(
				localStorage.token,
				res.collection_name,
				res.filename,
				transformFileName(res.filename),
				res.filename
			).catch((error) => {
				toast.error(error);
				return null;
			});
			await documents.set(await getDocs(localStorage.token));
		}
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={shareChatId} />
<ArchivedChatsModal
	bind:show={showArchivedChatsModal}
	on:change={async () => {
		await chats.set(await getChatList(localStorage.token));
	}}
/>

<div
	bind:this={navElement}
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen {$showSidebar
		? 'lg:relative w-[260px]'
		: '-translate-x-[260px] w-[0px]'} bg-[#ffffff80] text-gray-900 dark:bg-gray-950 dark:text-gray-200 text-sm transition fixed z-50 top-0 left-0 rounded-r-2xl
        "
	data-state={$showSidebar}
>
	<div
		class="py-2.5 my-auto flex flex-col h-screen min-h-screen w-[260px] {$showSidebar
			? ''
			: 'invisible'}"
	>
		

		<!-- {#if $user?.role === 'admin'}
			<div class="px-2 flex justify-center mt-0.5">
				<a
					class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/modelfiles"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');
					}}
				>
					<div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-4 h-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
							/>
						</svg>
					</div>

					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('Modelfiles')}</div>
					</div>
				</a>
			</div>

			<div class="px-2 flex justify-center">
				<a
					class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/prompts"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');
					}}
				>
					<div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-4 h-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
							/>
						</svg>
					</div>

					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('Prompts')}</div>
					</div>
				</a>
			</div>

			<div class="px-2 flex justify-center mb-1">
				<a
					class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/documents"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');
					}}
				>
					<div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-4 h-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
							/>
						</svg>
					</div>

					<div class="flex self-center">
						<div class=" self-center font-medium text-sm">{$i18n.t('Documents')}</div>
					</div>
				</a>
			</div>
		{/if} -->

		<!-- <button 
			class="ml-5 my-2 py-2 w-2/3 px-1.5 py-0.75 bg-gray-200 rounded-3xl hover:bg-gray-300"
			on:click={() => {
				filesInputElement.click();
			}}
		>
			+ New document
		</button> -->
		<input
						bind:this={filesInputElement}
						bind:files={inputFiles}
						type="file"
						hidden
						multiple
						on:change={async () => {
							if (inputFiles && inputFiles.length > 0) {
								const _inputFiles = Array.from(inputFiles);
								_inputFiles.forEach((file) => {
									if (
										SUPPORTED_FILE_TYPE.includes(file['type']) ||
										SUPPORTED_FILE_EXTENSIONS.includes(file.name.split('.').at(-1))
									) {
										uploadDoc(file);
										filesInputElement.value = '';
									} else {
										toast.error(
											$i18n.t(
												`Unknown File Type '{{file_type}}', but accepting and treating as plain text`,
												{ file_type: file['type'] }
											)
										);
										uploadDoc(file);
										filesInputElement.value = '';
									}
								});
							} else {
								toast.error($i18n.t(`File not found.`));
							}
						}}
					/>
		<div class="px-5 py-2 text-[#555] dark:text-[#aaa]">Recent Documents</div>
			<!-- FILE LIST -->
		<div class="relative flex flex-col overflow-y-auto px-4 max-h-[38%]">
			{#each filteredDocs as doc}
				<div 
				class=" flex items-center space-x-3 rounded-xl px-3.5 py-1.5 hover:bg-gray-100 dark:hover:bg-[#33333320]"
				>
					<div class="dark:text-[#999]">
						<svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
							<g clip-path="url(#clip0_1_16)">
							<path d="M10.7775 11.1525H1.2225C0.924135 11.1525 0.637987 11.034 0.427009 10.823C0.21603 10.612 0.0975037 10.3259 0.0975037 10.0275V1.9875C0.0975037 1.68913 0.21603 1.40298 0.427009 1.19201C0.637987 0.981027 0.924135 0.862501 1.2225 0.862501H4.5C4.66304 0.861414 4.82429 0.896503 4.97214 0.965238C5.11999 1.03397 5.25075 1.13465 5.355 1.26L6.0225 2.01C6.05773 2.05087 6.10153 2.08349 6.15079 2.10552C6.20005 2.12756 6.25355 2.13848 6.3075 2.1375L10.755 2.0925C11.0548 2.09447 11.3417 2.21441 11.5536 2.42637C11.7656 2.63833 11.8855 2.92525 11.8875 3.225V9.975C11.8935 10.1256 11.8694 10.2759 11.8166 10.417C11.7638 10.5582 11.6834 10.6874 11.58 10.797C11.4766 10.9067 11.3524 10.9946 11.2146 11.0557C11.0768 11.1167 10.9282 11.1496 10.7775 11.1525ZM1.2225 1.6125C1.12305 1.6125 1.02766 1.65201 0.957339 1.72234C0.887012 1.79266 0.847504 1.88804 0.847504 1.9875V10.0275C0.847504 10.127 0.887012 10.2223 0.957339 10.2927C1.02766 10.363 1.12305 10.4025 1.2225 10.4025H10.7775C10.8777 10.4025 10.9738 10.3633 11.0454 10.2931C11.1169 10.223 11.158 10.1276 11.16 10.0275V3.2775C11.16 3.17606 11.1197 3.07877 11.048 3.00703C10.9762 2.9353 10.8789 2.895 10.7775 2.895L6.3375 2.94C6.17052 2.9448 6.00485 2.9091 5.85465 2.83596C5.70446 2.76283 5.5742 2.65442 5.475 2.52L4.815 1.77C4.77813 1.72131 4.73053 1.68178 4.6759 1.65446C4.62127 1.62715 4.56108 1.61279 4.5 1.6125H1.2225Z" fill="#323333"/>
							</g>
							<defs>
							<clipPath id="clip0_1_16">
							<rect width="12" height="12" fill="white"/>
							</clipPath>
							</defs>
							</svg>
					</div>
					<!-- <Tooltip content={doc.name}> -->
						<div class="overflow-hidden whitespace-nowrap text-ellipsis">{doc.name}</div>
					<!-- </Tooltip> -->
				</div>
			{/each}
			<!-- {#if !($settings.saveChatHistory ?? true)}
				<div class="absolute z-40 w-full h-full bg-gray-50/90 dark:bg-black/90 flex justify-center">
					<div class=" text-left px-5 py-2">
						<div class=" font-medium">{$i18n.t('Chat History is off for this browser.')}</div>
						<div class="text-xs mt-2">
							{$i18n.t(
								"When history is turned off, new chats on this browser won't appear in your history on any of your devices."
							)}
							<span class=" font-semibold"
								>{$i18n.t('This setting does not sync across browsers or devices.')}</span
							>
						</div>

						<div class="mt-3">
							<button
								class="flex justify-center items-center space-x-1.5 px-3 py-2.5 rounded-lg text-xs bg-gray-100 hover:bg-gray-200 transition text-gray-800 font-medium w-full"
								type="button"
								on:click={() => {
									saveSettings({
										saveChatHistory: true
									});
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-3 h-3"
								>
									<path
										fill-rule="evenodd"
										d="M8 1a.75.75 0 0 1 .75.75v6.5a.75.75 0 0 1-1.5 0v-6.5A.75.75 0 0 1 8 1ZM4.11 3.05a.75.75 0 0 1 0 1.06 5.5 5.5 0 1 0 7.78 0 .75.75 0 0 1 1.06-1.06 7 7 0 1 1-9.9 0 .75.75 0 0 1 1.06 0Z"
										clip-rule="evenodd"
									/>
								</svg>

								<div>{$i18n.t('Enable Chat History')}</div>
							</button>
						</div>
					</div>
				</div>
			{/if} -->

			

			
		</div>

		<!-- SHOW MORE -->
		{#if $documents.length > 5}
		<button
			class="px-5 py-2 text-gray flex items-center"
			on:click={() => {
				showMoreDoc = !showMoreDoc
				// filteredDocs = showMoreDoc ? 
				// 	$documents
				// 	: $documents.slice(0,5)
				arrowClass = showMoreDoc ? 'rotate-180' : ''
			}}
		>
			<div class={arrowClass}>
				<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M6.06666 9.33333C5.53333 9.33333 5.06666 9.13333 4.66666 8.73333L0.866659 4.46667C0.599993 4.2 0.666659 3.8 0.933326 3.53333C1.19999 3.26667 1.59999 3.33333 1.86666 3.6L5.73333 7.86666C5.79999 7.93333 5.93333 8 6.06666 8C6.19999 8 6.33333 7.93333 6.46666 7.8L10.1333 3.53333C10.4 3.26667 10.8 3.2 11.0667 3.46667C11.3333 3.73333 11.4 4.13333 11.1333 4.4L7.46666 8.66667C7.13333 9.13333 6.66666 9.33333 6.06666 9.33333Z" fill="#555555"/>
				</svg>
			</div>
			<div class="ml-2 text-[#555]">{showMoreDoc ? 'Show less' : 'Show more'}</div>
		</button>
		{/if}

		<!-- New Chat -->
		<div class="px-2 mt-4 flex space-x-2">
			<!-- <Tooltip content="Start a new chat" placement="right"> -->
				<a
					id="sidebar-new-chat-button"
					class="flex-grow flex justify-between rounded-xl px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition font-semibold"
					href="/"
					on:click={async () => {
						selectedChatId = null;

						await goto('/');
						const newChatButton = document.getElementById('new-chat-button');
						setTimeout(() => {
							newChatButton?.click();
						}, 0);
					}}
				>
					Start New Chat<span>+</span>
					<!-- <div class="flex self-center">
						<div class="self-center mr-1.5">
							<img
								src="{WEBUI_BASE_URL}/static/favicon.ico"
								class=" size-6 -translate-x-1.5 rounded-full"
								alt="logo"
							/>
						</div>

						<div class=" self-center font-medium text-sm">{$i18n.t('New Chat')}</div> -->
						<!-- <img
							src="/logo-mbzuai.svg"
							alt="logo-mbzuai"
						/>
						<img
							src="/logo-ciai.svg"
							class="ml-4 size-14"
							alt="logo-ciai"
						/>
					</div> -->

					<!-- <div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
							/>
							<path
								d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
							/>
						</svg>
					</div> -->
				</a>
			<!-- </Tooltip> -->
		</div>
		<!-- Search Input  -->
		<div class="px-2 mt-2 mb-2 flex justify-center space-x-2">
			<div class="flex w-full" id="chat-search">
				<div class="self-center pl-3 py-2 rounded-l-xl bg-white dark:bg-gray-950">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>

				<input
					class="w-full rounded-r-xl py-1.5 pl-2.5 pr-4 text-sm dark:text-gray-300 dark:bg-gray-950 outline-none"
					placeholder='Search Chat'
					bind:value={search}
					on:focus={() => {
						enrichChatsWithContent($chats);
					}}
				/>
			</div>
		</div>

		<!-- <div class="px-5 py-2 mt-2 w-full text-[#555]">Chat History</div> -->
		<div class="relative flex flex-col overflow-y-auto px-2 max-h-[40%]">
			{#if $tags.length > 0}
				<div class="px-2.5 mt-0.5 mb-2 flex gap-1 flex-wrap">
					<button
						class="px-2.5 text-xs font-medium bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-800 transition rounded-full"
						on:click={async () => {
							await chats.set(await getChatList(localStorage.token));
						}}
					>
						all
					</button>
					{#each $tags as tag}
						<button
							class="px-2.5 text-xs font-medium bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-800 transition rounded-full"
							on:click={async () => {
								let chatIds = await getChatListByTagName(localStorage.token, tag.name);
								if (chatIds.length === 0) {
									await tags.set(await getAllChatTags(localStorage.token));
									chatIds = await getChatList(localStorage.token);
								}
								await chats.set(chatIds);
							}}
						>
							{tag.name}
						</button>
					{/each}
				</div>
			{/if}

			<div class="pl-2 my-2 flex-1 flex flex-col space-y-1 overflow-y-auto scrollbar-none">
				{#each $chats.filter((chat) => {
					if (search === '') {
						return true;
					} else {
						let title = chat.title.toLowerCase();
						const query = search.toLowerCase();

						let contentMatches = false;
						// Access the messages within chat.chat.messages
						if (chat.chat && chat.chat.messages && Array.isArray(chat.chat.messages)) {
							contentMatches = chat.chat.messages.some((message) => {
								// Check if message.content exists and includes the search query
								return message.content && message.content.toLowerCase().includes(query);
							});
						}

						return title.includes(query) || contentMatches;
					}
				}) as chat, i}
					<div class=" w-full pr-2 relative group">
						{#if chatTitleEditId === chat.id}
							<div
								class=" w-full flex justify-between rounded-xl px-3 py-2 {chat.id === $chatId ||
								chat.id === chatTitleEditId ||
								chat.id === chatDeleteId
									? 'bg-gray-200 dark:bg-gray-900'
									: chat.id === selectedChatId
									? 'bg-gray-100 dark:bg-gray-950'
									: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis"
							>
								<input bind:value={chatTitle} class=" bg-transparent w-full outline-none mr-10" />
							</div>
						{:else}
							<a
								class=" w-full flex justify-between rounded-xl px-3 py-2 {chat.id === $chatId ||
								chat.id === chatTitleEditId ||
								chat.id === chatDeleteId
									? 'bg-gray-200 dark:bg-gray-900'
									: chat.id === selectedChatId
									? 'bg-gray-100 dark:bg-gray-950'
									: ' group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis"
								href="/c/{chat.id}"
								on:click={() => {
									selectedChatId = chat.id;
									if (window.innerWidth < 1024) {
										showSidebar.set(false);
									}
								}}
								draggable="false"
							>
								<div class=" flex self-center flex-1 w-full">
									<div class=" text-left self-center overflow-hidden w-full h-[20px]">
										{chat.title}
									</div>
								</div>
							</a>
						{/if}

						<div
							class="

							{chat.id === $chatId || chat.id === chatTitleEditId || chat.id === chatDeleteId
								? 'from-gray-200 dark:from-gray-900'
								: chat.id === selectedChatId
								? 'from-gray-100 dark:from-gray-950'
								: 'invisible group-hover:visible from-gray-100 dark:from-gray-950'}
								absolute right-[10px] top-[10px] pr-2 pl-5 bg-gradient-to-l from-80%

								  to-transparent"
						>
							{#if chatTitleEditId === chat.id}
								<div class="flex self-center space-x-1.5 z-10">
									<button
										class=" self-center dark:hover:text-white transition"
										on:click={() => {
											editChatTitle(chat.id, chatTitle);
											chatTitleEditId = null;
											chatTitle = '';
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
									<button
										class=" self-center dark:hover:text-white transition"
										on:click={() => {
											chatTitleEditId = null;
											chatTitle = '';
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
											/>
										</svg>
									</button>
								</div>
							{:else if chatDeleteId === chat.id}
								<div class="flex self-center space-x-1.5 z-10">
									<button
										class=" self-center dark:hover:text-white transition"
										on:click={() => {
											deleteChat(chat.id);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
									<button
										class=" self-center dark:hover:text-white transition"
										on:click={() => {
											chatDeleteId = null;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
											/>
										</svg>
									</button>
								</div>
							{:else}
								<div class="flex self-center space-x-1 z-10">
									<ChatMenu
										chatId={chat.id}
										shareHandler={() => {
											shareChatId = selectedChatId;
											showShareChatModal = true;
										}}
										renameHandler={() => {
											chatTitle = chat.title;
											chatTitleEditId = chat.id;
										}}
										deleteHandler={() => {
											chatDeleteId = chat.id;
										}}
										onClose={() => {
											selectedChatId = null;
										}}
									>
										<button
											aria-label="Chat Menu"
											class=" self-center dark:hover:text-white transition"
											on:click={() => {
												selectedChatId = chat.id;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
												/>
											</svg>
										</button>
									</ChatMenu>

									<Tooltip content={$i18n.t('Archive')}>
										<button
											aria-label="Archive"
											class=" self-center dark:hover:text-white transition"
											on:click={() => {
												archiveChatHandler(chat.id);
											}}
										>
											<ArchiveBox />
										</button>
									</Tooltip>

									{#if chat.id === $chatId}
										<button
											id="delete-chat-button"
											class="hidden"
											on:click={() => {
												chatDeleteId = chat.id;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
												/>
											</svg>
										</button>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>

		<div class="px-2.5 flex-1 flex flex-col justify-end">
			<!-- <hr class=" border-gray-900 mb-1 w-full" /> -->
				<!-- <button
					class="cursor-pointer p-1.5 flex items-center dark:hover:bg-gray-700 rounded-full transition"
					id="open-settings-button"
					on:click={async () => {
						await showSettings.set(!$showSettings);
					}}
				>
					<svg width="24" height="24" viewBox="0 0 27 27" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M15 3V6L16.05 6.3C16.35 6.45 16.5 6.45 16.8 6.6L17.7 7.05L18.45 6.3L19.8 4.95L21 6.15L22.05 7.2L20.55 8.7L19.8 9.45L20.25 10.35C20.4 10.5 20.4 10.8 20.55 10.95L21 12H24V15H21L20.7 16.05C20.55 16.35 20.55 16.5 20.4 16.8L19.95 17.7L20.7 18.45L22.2 19.95L20.1 22.05L18.6 20.55L17.85 19.8L16.95 20.25C16.65 20.4 16.5 20.4 16.2 20.55L15 21V24H12V21L10.95 20.7C10.8 20.7 10.5 20.55 10.35 20.4L9.45 19.95L8.7 20.7L7.2 22.2L6.15 21L5.1 19.95L6.45 18.6L7.2 17.85L6.75 16.95C6.6 16.65 6.6 16.5 6.45 16.2L6 15H3V12H6L6.3 10.95C6.45 10.8 6.6 10.5 6.75 10.2L7.2 9.3L6.45 8.55L5.1 7.2L7.2 5.1L8.55 6.45L9.3 7.2L10.2 6.75C10.5 6.6 10.8 6.45 10.95 6.45L12 6V3H15ZM16.5 1.5H10.5V4.95L9.6 5.4L7.2 3L3 7.2L5.4 9.6L4.95 10.5H1.5V16.5H4.95C5.1 16.8 5.25 17.1 5.25 17.4L2.7 19.95L4.8 22.05L6.9 24.15L9.45 21.6C9.75 21.75 9.9 21.75 10.2 21.9V25.5H16.2V22.05C16.5 21.9 16.8 21.75 17.1 21.75L19.65 24.3L23.85 20.1L21.3 17.55C21.45 17.25 21.6 16.95 21.6 16.65H25.5V10.5H22.05C21.9 10.2 21.9 10.05 21.75 9.75L24.3 7.2L22.2 5.1L20.1 3L17.55 5.55C17.25 5.4 16.95 5.25 16.65 5.25V1.5H16.5Z" fill="#545454"/>
						<path d="M13.5 18C10.95 18 9 16.05 9 13.5C9 10.95 10.95 9 13.5 9C16.05 9 18 10.95 18 13.5C18 16.05 16.05 18 13.5 18ZM13.5 16.5C15.15 16.5 16.5 15.15 16.5 13.5C16.5 11.85 15.15 10.5 13.5 10.5C11.85 10.5 10.5 11.85 10.5 13.5C10.5 15.15 11.85 16.5 13.5 16.5Z" fill="#545454"/>
					</svg>
					<span class="ml-3">{$i18n.t('Settings')}</span>
				</button> -->
				<!-- <button
					class="cursor-pointer p-1 flex items-center dark:hover:bg-gray-700 rounded-full transition"
					id="open-settings-button"
					on:click={async () => {
						await showSettings.set(!$showSettings);
					}}
				>
					<svg width="28" height="28" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M16.609 18.445L4.64099 12.359L17.017 5.21899L28.968 11.9L16.609 18.445ZM8.53399 12.257L16.592 16.354L25.092 11.866L17.034 7.36099L8.53399 12.257Z" fill="#545454"/>
					<path d="M16.575 23.069L5.032 17.17L5.882 15.521L16.558 20.978L27.727 15.062L28.594 16.694L16.575 23.069Z" fill="#545454"/>
					<path d="M16.575 28.526L5.032 22.423L5.899 20.774L16.558 26.435L27.71 20.315L28.611 21.93L16.575 28.526Z" fill="#545454"/>
					</svg>
					
					<span class="ml-3">LLama3 (Model name here)</span>
				</button> -->
			<!-- <div class="flex flex-col">
				{#if $user !== undefined}
					<button
						class=" flex rounded-xl py-3 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
						on:click={() => {
							showDropdown = !showDropdown;
						}}
					>
						<div class=" self-center mr-3">
							<img
								src={$user.profile_image_url}
								class=" max-w-[30px] object-cover rounded-full"
								alt="User profile"
							/>
						</div>
						<div class=" self-center font-semibold">{$user.name}</div>
					</button>

					{#if showDropdown}
						<div
							id="dropdownDots"
							class="absolute z-40 bottom-[70px] rounded-lg shadow w-[240px] bg-white dark:bg-gray-900"
							transition:fade|slide={{ duration: 100 }}
						>
							<div class="p-1 py-2 w-full">
								{#if $user.role === 'admin'}
									<button
										class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
										on:click={() => {
											goto('/admin');
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
													d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z"
												/>
											</svg>
										</div>
										<div class=" self-center font-medium">{$i18n.t('Admin Panel')}</div>
									</button>

									<button
										class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
										on:click={() => {
											goto('/playground');
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
													d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z"
												/>
											</svg>
										</div>
										<div class=" self-center font-medium">{$i18n.t('Playground')}</div>
									</button>
								{/if}

								<button
									class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
									on:click={() => {
										showArchivedChatsModal = true;
										showDropdown = false;
									}}
								>
									<div class=" self-center mr-3">
										<ArchiveBox className="size-5" strokeWidth="1.5" />
									</div>
									<div class=" self-center font-medium">{$i18n.t('Archived Chats')}</div>
								</button>

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
			</div> -->
		</div>
	</div>

	<div
		id="sidebar-handle"
		class="fixed left-0 top-[50dvh] -translate-y-1/2 transition-transform translate-x-[255px] md:translate-x-[260px] rotate-0"
	>
		<Tooltip
			placement="right"
			content={`${$showSidebar ? $i18n.t('Close') : $i18n.t('Open')} ${$i18n.t('sidebar')}`}
			touch={false}
		>
			<button
				id="sidebar-toggle-button"
				class=" group"
				on:click={() => {
					showSidebar.set(!$showSidebar);
				}}
				><span class="" data-state="closed"
					><div
						class="flex h-[72px] w-8 items-center justify-center opacity-50 group-hover:opacity-100 transition"
					>
						<div class="flex h-6 w-6 flex-col items-center">
							<div
								class="h-3 w-1 rounded-full bg-[#0f0f0f] dark:bg-white rotate-0 translate-y-[0.15rem] {show
									? 'group-hover:rotate-[15deg]'
									: 'group-hover:rotate-[-15deg]'}"
							/>
							<div
								class="h-3 w-1 rounded-full bg-[#0f0f0f] dark:bg-white rotate-0 translate-y-[-0.15rem] {show
									? 'group-hover:rotate-[-15deg]'
									: 'group-hover:rotate-[15deg]'}"
							/>
						</div>
					</div>
				</span>
			</button>
		</Tooltip>
	</div>
</div>

<style>
	.scrollbar-none:active::-webkit-scrollbar-thumb,
	.scrollbar-none:focus::-webkit-scrollbar-thumb,
	.scrollbar-none:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-none::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
