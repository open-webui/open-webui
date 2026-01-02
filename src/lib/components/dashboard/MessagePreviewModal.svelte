<script lang="ts">
	import { createEventDispatcher, getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import type { TagMessageInfo } from '$lib/apis/message-tags';
	import { getChatById, getChatByShareId } from '$lib/apis/chats';
	import { getTextbookData, type Chapter, type Section } from '$lib/apis/textbook';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let message: TagMessageInfo | null = null;
	export let tagName: string = '';

	let loadingChat = false;
	let chatData: any = null;
	let chatError: string | null = null;
	let textbookChaptersCache: Chapter[] = [];
	let chapterTitle: string = '';

	// Load textbook chapters for chapter_id lookup
	const loadTextbookChapters = async () => {
		if (textbookChaptersCache.length > 0) return;
		try {
			const data = await getTextbookData(localStorage.token);
			if (data?.sections) {
				textbookChaptersCache = data.sections.flatMap((section: Section) => section.subsections);
			}
		} catch (error) {
			console.error('Failed to load textbook data:', error);
		}
	};

	// Find chapter by chapter_id
	const findChapterById = (chapterId: string): Chapter | null => {
		return textbookChaptersCache.find((ch: Chapter) => ch.id === chapterId) || null;
	};

	// Format timestamp
	const formatDate = (timestamp: number) => {
		return new Date(timestamp * 1000).toLocaleString('ko-KR', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	// Scroll to target message
	const scrollToMessage = async (messageId: string) => {
		// Find message index for logging
		const messageIndex = messages.findIndex((msg: any) => msg.id === messageId);
		console.log('Scrolling to message:', {
			messageId,
			messageIndex,
			totalMessages: messages.length,
			found: messageIndex !== -1
		});

		// Wait for DOM to be fully updated
		await tick();
		await tick(); // Double tick for safety
		
		// Add a small delay to ensure rendering is complete
		setTimeout(() => {
			const element = document.getElementById(`message-${messageId}`);
			console.log('Element found:', element);
			
			if (element) {
				element.scrollIntoView({ behavior: 'smooth', block: 'center' });
				// Add highlight effect
				element.classList.add('highlight-message');
				setTimeout(() => {
					element.classList.remove('highlight-message');
				}, 2000);
			} else {
				console.warn('Message element not found in DOM');
			}
		}, 300);
	};

	// Load full chat when modal opens
	const loadFullChat = async () => {
		if (!message) return;

		loadingChat = true;
		chatError = null;

		try {
			// Admin uses getChatByShareId with chat_id to access other users' chats
			// Regular users use getChatById
			const result = $user?.role === 'admin' 
				? await getChatByShareId(localStorage.token, message.chat_id)
				: await getChatById(localStorage.token, message.chat_id);
				
			if (result) {
				chatData = result;
				
				// Load chapter title if chapter_id exists
				if (chatData.chapter_id) {
					if (chatData.chat?.chapter) {
						// Use existing chapter title from chat data
						chapterTitle = chatData.chat.chapter;
					} else {
						// Load from textbook API if not in chat data
						await loadTextbookChapters();
						const chapter = findChapterById(chatData.chapter_id);
						if (chapter) {
							chapterTitle = chapter.title;
						}
					}
				} else {
					chapterTitle = '';
				}
				
				// Scroll to the target message after chat is loaded
				if (message.message_id) {
					await scrollToMessage(message.message_id);
				}
			}
		} catch (error) {
			console.error('Failed to load chat:', error);
			chatError = typeof error === 'string' ? error : '대화를 불러오는데 실패했습니다.';
		} finally {
			loadingChat = false;
		}
	};

	// Load chat when modal is shown
	$: if (show && message) {
		loadFullChat();
	}

	// Reset state when modal closes
	$: if (!show) {
		chatData = null;
		chatError = null;
		chapterTitle = '';
	}

	// Extract messages from chat data
	$: messages = chatData?.chat?.messages
		? Object.values(chatData.chat.messages).sort((a: any, b: any) => {
				// Sort by timestamp if available
				const timeA = a.timestamp || 0;
				const timeB = b.timestamp || 0;
				return timeA - timeB;
			})
		: [];
</script>

<style>
	:global(.highlight-message) {
		animation: highlight 2s ease-in-out;
	}

	@keyframes highlight {
		0% {
			box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5);
		}
		50% {
			box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.3);
		}
		100% {
			box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
		}
	}
</style>

<Modal bind:show size="lg">
	<div class="p-6 max-h-[80vh] overflow-hidden flex flex-col">
		{#if message}
			<!-- Header -->
			<div class="flex items-start justify-between mb-4 shrink-0">
				<div class="flex items-center gap-3">
					<!-- Tag Badge -->
					<div class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-sm">
						<svg width="14" height="14" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" class="shrink-0">
							<path d="M3.33333 10.8333L10.8333 3.33333H16.6667V9.16667L9.16667 16.6667L3.33333 10.8333Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
							<circle cx="13.3333" cy="6.66667" r="1.25" fill="currentColor"/>
						</svg>
						<span class="font-medium">{tagName}</span>
					</div>
					<div class="flex flex-col gap-1">
						{#if chapterTitle}
							<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
								{chapterTitle}
							</span>
						{/if}
						{#if chatData?.chat?.title}
							<span class="text-sm text-gray-500 dark:text-gray-400">
								{chatData.chat.title}
							</span>
						{/if}
					</div>
				</div>
				<!-- Close Button -->
				<button
					on:click={() => (show = false)}
					class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto min-h-0 space-y-6">
				<!-- Summary Section -->
				<div>
					<h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
						{$i18n.t('요약')}
					</h4>
					<div class="p-4 bg-gray-50 dark:bg-gray-850 rounded-xl">
						<p class="text-base text-gray-900 dark:text-white leading-relaxed">
							{message.summary || $i18n.t('요약 정보가 없습니다.')}
						</p>
					</div>

					<!-- Meta Info -->
					<div class="flex flex-wrap gap-4 pt-3">
						<!-- User -->
						<div class="flex items-center gap-2">
							<svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
							</svg>
							<span class="text-sm text-gray-600 dark:text-gray-400">{message.user_name}</span>
						</div>
						<!-- Time -->
						<div class="flex items-center gap-2">
							<svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<span class="text-sm text-gray-600 dark:text-gray-400">{formatDate(message.created_at)}</span>
						</div>
					</div>
				</div>

				<!-- Divider -->
				<div class="border-t border-gray-200 dark:border-gray-700"></div>

				<!-- Full Chat Section -->
				<div>
					<h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
						{$i18n.t('전체 대화')}
					</h4>
					{#if loadingChat}
						<div class="flex items-center justify-center py-8">
							<Spinner className="w-6 h-6" />
							<span class="ml-2 text-gray-500">{$i18n.t('로딩 중...')}</span>
						</div>
					{:else if chatError}
						<div class="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-center">
							{chatError}
						</div>
					{:else if messages.length === 0}
						<div class="p-4 text-gray-500 dark:text-gray-400 text-center">
							{$i18n.t('대화 내용이 없습니다.')}
						</div>
					{:else}
						<div class="space-y-4">
							{#each messages as msg, idx (msg.id || idx)}
								<div 
									id="message-{msg.id}"
									class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}"
								>
									<div class="max-w-[85%] {msg.role === 'user'
										? 'bg-blue-600 text-white rounded-2xl rounded-br-md'
										: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-2xl rounded-bl-md'} px-4 py-3 transition-shadow duration-300">
										<!-- Role Label -->
										<div class="text-xs {msg.role === 'user' ? 'text-blue-200' : 'text-gray-500 dark:text-gray-400'} mb-1 font-medium">
											{msg.role === 'user' ? message.user_name : 'AI'}
										</div>
										<!-- Message Content -->
									<div class="text-sm break-words leading-relaxed">
										{#if typeof msg.content === 'string'}
											{#if msg.role === 'assistant'}
												<Markdown id={msg.id} content={msg.content} />
											{:else}
												<div class="whitespace-pre-wrap">{msg.content}</div>
											{/if}
										{:else if Array.isArray(msg.content)}
											{#each msg.content as part}
												{#if part.type === 'text'}
													{#if msg.role === 'assistant'}
														<Markdown id={msg.id} content={part.text} />
													{:else}
														<div class="whitespace-pre-wrap">{part.text}</div>
													{/if}
													{/if}
												{/each}
											{/if}
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>

			<!-- Footer -->
			<div class="flex justify-end gap-3 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800 shrink-0">
				<button
					on:click={() => (show = false)}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				>
					{$i18n.t('닫기')}
				</button>
			</div>
		{/if}
	</div>
</Modal>
