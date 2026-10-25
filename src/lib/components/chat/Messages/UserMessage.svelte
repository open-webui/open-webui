<script lang="ts">
	import EditPencilIcon from '$lib/components/layout/Sidebar/icons/EditPencil.svelte';
	import CopyIcon from '$lib/components/layout/Sidebar/icons/Copy.svelte';
	import TrashIcon from '$lib/components/layout/Sidebar/icons/Trash.svelte';
	import ChevronRightIcon from '$lib/components/layout/Sidebar/icons/ChevronRight.svelte';
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	import { models, settings } from '$lib/stores';
	import { user as _user } from '$lib/stores';
	import {
		copyToClipboard as _copyToClipboard,
		formatMessageTimestamp,
		formatMessageTimestampFull,
		isRasterImageContentType
	} from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import equal from 'fast-deep-equal';

	import Name from './Name.svelte';
	import ContextCompactionLabel from './ContextCompactionLabel.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Markdown from './Markdown.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import SubagentResultRow from './SubagentResultRow.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const contextCompactions =
		getContext<Writable<Record<string, 'in_progress' | { error: string }>>>('contextCompactions');
	export let user;

	export let chatId;
	export let history;
	export let messageId;

	export let siblings;

	export let gotoMessage: Function;
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let editMessage: Function;
	export let deleteMessage: Function;

	export let isFirstMessage: boolean;
	export let readOnly: boolean;
	export let shareMode: 'continue' | null = null;
	export let allowDelete = true;
	export let compactPreview = false;
	export let editCodeBlock = true;
	export let topPadding = false;

	let showDeleteConfirm = false;

	let messageIndexEdit = false;

	let edit = false;
	let editedContent = '';
	let editedFiles = [];

	let messageEditTextAreaElement: HTMLTextAreaElement;
	let editScrollContainer: HTMLDivElement;

	let message = structuredClone(history.messages[messageId]);
	$: authorId = message.user_id || message.user?.id || user?.id;
	$: author =
		message.user?.id === authorId
			? message.user
			: $_user?.id === authorId
				? $_user
				: user?.id === authorId
					? user
					: null;
	$: isOwn = Boolean($_user?.id && authorId === $_user.id);
	$: authorName = author?.name || $i18n.t('Unknown User');
	let timerExpanded = false;
	$: if (history.messages) {
		const source = history.messages[messageId];
		if (source) {
			if (message.content !== source.content) {
				message = structuredClone(source);
			} else if (!equal(message, source)) {
				message = structuredClone(source);
			}
		}
	}
	const copyToClipboard = async (text) => {
		const res = await _copyToClipboard(text);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const editMessageHandler = async () => {
		edit = true;
		editedContent = message?.content ?? '';
		editedFiles = [...(message.files ?? [])];

		await tick();

		if (messageEditTextAreaElement) {
			const messagesContainer = document.getElementById('messages-container');
			const savedScrollTop = messagesContainer?.scrollTop;

			messageEditTextAreaElement.style.height = '';
			messageEditTextAreaElement.style.height = `${messageEditTextAreaElement.scrollHeight}px`;

			if (messagesContainer) messagesContainer.scrollTop = savedScrollTop;
			messageEditTextAreaElement?.focus({ preventScroll: true });
		}
	};

	const editMessageConfirmHandler = async (submit = true) => {
		if (!editedContent && (editedFiles ?? []).length === 0) {
			toast.error($i18n.t('Please enter a message or attach a file.'));
			return;
		}

		editMessage(message.id, { content: editedContent, files: editedFiles }, submit);

		edit = false;
		editedContent = '';
		editedFiles = [];
	};

	const cancelEditMessage = () => {
		edit = false;
		editedContent = '';
		editedFiles = [];
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	onMount(() => {
		// console.log('UserMessage mounted');
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

<div
	class="flex w-full user-message group {!isOwn && !message?.meta?.internal
		? compactPreview
			? 'my-2'
			: 'mb-2'
		: ''}"
	dir={$settings.chatDirection}
	id="message-{message.id}"
	style="scroll-margin-top: 3rem;"
>
	{#if !compactPreview && (!($settings?.chatBubble ?? true) || !isOwn) && !(message?.meta?.internal === true && message?.meta?.type === 'subagent') && !(message?.meta?.internal === true && message?.meta?.type === 'timer')}
		<div
			class="shrink-0 me-2 {($settings?.chatBubble ?? true) ? 'mt-6' : 'hidden @lg:flex mt-0.5'}"
		>
			<!-- LICENSE covers this Open WebUI fallback logo.
			Do not alter, remove, obscure, or replace it except as LICENSE permits:
			https://docs.openwebui.com/license. -->
			<ProfilePreview user={{ id: authorId, name: authorName }}>
				<ProfileImage
					src={authorId
						? `${WEBUI_API_BASE_URL}/users/${authorId}/profile/image`
						: `${WEBUI_BASE_URL}/static/favicon.png`}
					className={'size-7 user-message-profile-image'}
				/>
			</ProfilePreview>
		</div>
	{/if}
	<div
		class="flex-auto w-0 max-w-full {(message?.meta?.internal === true &&
			message?.meta?.type === 'subagent') ||
		(message?.meta?.internal === true && message?.meta?.type === 'timer')
			? ''
			: 'pl-1'}"
	>
		{#if !compactPreview && (!($settings?.chatBubble ?? true) || !isOwn) && !(message?.meta?.internal === true && message?.meta?.type === 'subagent') && !(message?.meta?.internal === true && message?.meta?.type === 'timer')}
			<div
				class={($settings?.chatBubble ?? true)
					? 'mb-1 ps-2 text-xs text-gray-400 dark:text-gray-500'
					: ''}
			>
				{#if $settings?.chatBubble ?? true}
					{authorName}
				{:else}
					<Name>{isOwn && !$settings.showUsername ? $i18n.t('You') : authorName}</Name>
				{/if}
			</div>
		{/if}

		{#if message.contextSummary || $contextCompactions?.[messageId]}
			<ContextCompactionLabel
				summary={message.contextSummary}
				status={$contextCompactions?.[messageId]}
				{compactPreview}
			/>
		{/if}

		<div class="chat-{message.role} w-full min-w-full">
			{#if edit !== true}
				{#if message.files}
					<div
						class="mb-1 w-full flex flex-col justify-end overflow-x-auto gap-1 flex-wrap"
						dir={$settings?.chatDirection ?? 'auto'}
					>
						{#each message.files as file}
							{@const fileUrl =
								file.url?.startsWith('data') || file.url?.startsWith('http')
									? file.url
									: `${WEBUI_API_BASE_URL}/files/${file.url}${file?.content_type ? '/content' : ''}`}
							<div
								class={($settings?.chatBubble ?? true) ? (isOwn ? 'self-end' : 'self-start') : ''}
							>
								{#if file.type === 'image' || isRasterImageContentType(file?.content_type)}
									<Image src={fileUrl} imageClassName=" max-h-96 rounded-lg" />
								{:else}
									<FileItem
										item={file}
										url={file.url}
										name={file.name}
										type={file.type}
										size={file?.size}
										small={true}
									/>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			{/if}

			{#if edit === true}
				<div
					class=" w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-4 py-3 mb-2 {($settings?.highContrastMode ??
					false)
						? 'focus-within:outline focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-blue-500'
						: ''}"
				>
					{#if (editedFiles ?? []).length > 0}
						<div class="flex items-center flex-wrap gap-2 -mx-2 mb-1">
							{#each editedFiles as file, fileIdx}
								{#if file.type === 'image' || isRasterImageContentType(file?.content_type)}
									{@const fileUrl =
										file.url?.startsWith('data') || file.url?.startsWith('http')
											? file.url
											: `${WEBUI_API_BASE_URL}/files/${file.url}${file?.content_type ? '/content' : ''}`}
									<div class=" relative group">
										<div class="relative flex items-center">
											<Image
												src={fileUrl}
												alt="input"
												imageClassName=" size-14 rounded-xl object-cover"
											/>
										</div>
										<div class=" absolute -top-1 -right-1">
											<button
												aria-label={$i18n.t('Remove file')}
												class=" bg-white text-black border border-white rounded-full {($settings?.highContrastMode ??
												false)
													? ''
													: 'hover-reveal transition'}"
												type="button"
												on:click={() => {
													editedFiles.splice(fileIdx, 1);

													editedFiles = editedFiles;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-4"
												>
													<path
														d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
													/>
												</svg>
											</button>
										</div>
									</div>
								{:else}
									<FileItem
										item={file}
										name={file.name}
										type={file.type}
										size={file?.size}
										loading={file.status === 'uploading'}
										dismissible={true}
										edit={true}
										on:dismiss={async () => {
											editedFiles.splice(fileIdx, 1);

											editedFiles = editedFiles;
										}}
										on:click={() => {
											console.log(file);
										}}
									/>
								{/if}
							{/each}
						</div>
					{/if}

					<div class="max-h-96 overflow-auto" bind:this={editScrollContainer}>
						<textarea
							id="message-edit-{message.id}"
							bind:this={messageEditTextAreaElement}
							class=" bg-transparent outline-hidden focus-visible:outline-none! w-full resize-none text-[0.9375rem]"
							bind:value={editedContent}
							on:input={(e) => {
								const messagesContainer = document.getElementById('messages-container');
								const savedScrollTop = messagesContainer?.scrollTop;
								const savedInnerScroll = editScrollContainer?.scrollTop;

								e.target.style.height = '';
								e.target.style.height = `${e.target.scrollHeight}px`;

								if (messagesContainer) messagesContainer.scrollTop = savedScrollTop;
								if (editScrollContainer) editScrollContainer.scrollTop = savedInnerScroll;
							}}
							on:keydown={(e) => {
								if (e.key === 'Escape') {
									document.getElementById('close-edit-message-button')?.click();
								}

								const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
								const isEnterPressed = e.key === 'Enter';

								if (isCmdOrCtrlPressed && isEnterPressed) {
									document.getElementById('confirm-edit-message-button')?.click();
								}
							}}
						/>
					</div>

					<div class=" mt-2 -mx-1 flex justify-between text-sm font-normal">
						<div>
							{#if isOwn && !readOnly}
								<button
									id="save-edit-message-button"
									class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 disabled:opacity-60 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
									on:click={() => {
										editMessageConfirmHandler(false);
									}}
								>
									{$i18n.t('Save')}
								</button>
							{/if}
						</div>

						<div class="flex space-x-1.5">
							<button
								id="close-edit-message-button"
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 disabled:opacity-60 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-white"
								on:click={() => {
									cancelEditMessage();
								}}
							>
								{$i18n.t('Cancel')}
							</button>

							<button
								id="confirm-edit-message-button"
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
								on:click={() => {
									editMessageConfirmHandler();
								}}
							>
								{$i18n.t('Send')}
							</button>
						</div>
					</div>
				</div>
			{:else if message?.meta?.internal === true && message?.meta?.type === 'timer'}
				<div class="w-full min-w-0">
					<button
						type="button"
						class="flex w-full min-w-0 items-center gap-2 text-left text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
						aria-expanded={timerExpanded}
						on:click={() => {
							timerExpanded = !timerExpanded;
						}}
					>
						<span class="shrink-0 text-[0.75rem] font-medium">{$i18n.t('Timer')}</span>
						<span class="min-w-0 flex-1 truncate text-[0.75rem]">{message.content}</span>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-3 shrink-0 text-gray-400 transition-transform duration-150 dark:text-gray-600 {timerExpanded
								? 'rotate-180'
								: ''}"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
						</svg>
					</button>
					{#if timerExpanded}
						<div
							class="mt-2 ml-3 whitespace-pre-wrap break-words border-l border-gray-100 pl-3 text-[0.78125rem] leading-relaxed text-gray-600 dark:border-white/10 dark:text-gray-400"
							dir={$settings?.chatDirection ?? 'auto'}
						>
							{message.content}
						</div>
					{/if}
				</div>
			{:else if message?.meta?.internal === true && message?.meta?.type === 'subagent'}
				<SubagentResultRow content={message.content} result={message.meta} />
			{:else if message.content !== ''}
				<div class="w-full">
					<div
						class="flex {($settings?.chatBubble ?? true)
							? `${isOwn ? 'justify-end' : 'justify-start'} pb-1`
							: 'w-full'}"
					>
						<div
							class="rounded-3xl {($settings?.chatBubble ?? true)
								? `max-w-[90%] px-4 py-1.5  bg-gray-50 dark:bg-gray-850 ${
										message.files ? (isOwn ? 'rounded-se-lg' : 'rounded-ss-lg') : ''
									}`
								: ' w-full'}"
						>
							{#if message.content}
								{#if $settings?.renderMarkdownInUserMessages ?? true}
									<div class="markdown-prose">
										<Markdown
											id={`${chatId}-${message.id}`}
											content={message.content}
											{editCodeBlock}
											{topPadding}
										/>
									</div>
								{:else}
									<div
										class="whitespace-pre-wrap text-[0.9375rem]"
										dir={$settings?.chatDirection ?? 'auto'}
									>
										{message.content}
									</div>
								{/if}
							{/if}
						</div>
					</div>
				</div>
			{/if}

			{#if edit !== true && !(message?.meta?.internal === true && message?.meta?.type === 'subagent') && !(message?.meta?.internal === true && message?.meta?.type === 'timer')}
				<div
					class="flex items-center {($settings?.chatBubble ?? true)
						? isOwn
							? 'justify-end'
							: 'justify-start'
						: 'items-center'}  {($settings?.highContrastMode ?? false)
						? 'text-gray-600 dark:text-gray-500'
						: 'text-gray-600/80 dark:text-gray-500/70'}"
				>
					{#if message.timestamp}
						<Tooltip
							className="flex self-center {($settings?.chatBubble ?? true) && isOwn
								? 'mr-1'
								: 'order-last'}"
							content={formatMessageTimestampFull(message.timestamp * 1000, $i18n.language)}
							placement="bottom"
						>
							<time
								datetime={new Date(message.timestamp * 1000).toISOString()}
								class="{compactPreview ? '' : 'hover-reveal'} {($settings?.chatBubble ?? true) &&
								isOwn
									? 'mr-1'
									: 'ml-1 shrink-0 whitespace-nowrap'} text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-600 select-none"
							>
								{formatMessageTimestamp(message.timestamp * 1000, $i18n.language)}
							</time>
						</Tooltip>
					{/if}

					{#if !compactPreview && (!($settings?.chatBubble ?? true) || !isOwn)}
						{#if siblings.length > 1}
							<div class="flex self-center" dir="ltr">
								<button
									aria-label={$i18n.t('Previous message')}
									class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
									on:click={() => {
										showPreviousMessage(message);
									}}
								>
									<ChevronRightIcon className="size-4 rotate-180" />
								</button>

								{#if messageIndexEdit}
									<div
										class="text-sm flex justify-center font-normal self-center dark:text-gray-500 min-w-fit"
									>
										<input
											id="message-index-input-{message.id}"
											type="number"
											value={siblings.indexOf(message.id) + 1}
											min="1"
											max={siblings.length}
											on:focus={(e) => {
												e.target.select();
											}}
											on:blur={(e) => {
												gotoMessage(message, e.target.value - 1);
												messageIndexEdit = false;
											}}
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}
											}}
											class="bg-transparent font-normal self-center dark:text-gray-500 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-normal self-center dark:text-gray-500 min-w-fit"
										on:dblclick={async () => {
											messageIndexEdit = true;

											await tick();
											const input = document.getElementById(`message-index-input-${message.id}`);
											if (input) {
												input.focus();
												input.select();
											}
										}}
									>
										{siblings.indexOf(message.id) + 1}/{siblings.length}
									</div>
								{/if}

								<button
									aria-label={$i18n.t('Next message')}
									class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
									on:click={() => {
										showNextMessage(message);
									}}
								>
									<ChevronRightIcon className="size-4" />
								</button>
							</div>
						{/if}
					{/if}
					{#if !compactPreview && (!readOnly || shareMode === 'continue') && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.edit ?? true))}
						<Tooltip content={$i18n.t('Edit')} placement="bottom">
							<button
								class="{($settings?.highContrastMode ?? false)
									? ''
									: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition edit-user-message-button"
								aria-label={$i18n.t('Edit')}
								on:click={() => {
									editMessageHandler();
								}}
							>
								<EditPencilIcon />
							</button>
						</Tooltip>
					{/if}

					{#if !compactPreview && message?.content}
						<Tooltip content={$i18n.t('Copy')} placement="bottom">
							<button
								class="{($settings?.highContrastMode ?? false)
									? ''
									: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
								aria-label={$i18n.t('Copy')}
								on:click={() => {
									copyToClipboard(message.content);
								}}
							>
								<CopyIcon />
							</button>
						</Tooltip>
					{/if}

					{#if $_user?.role === 'admin' || ($_user?.permissions?.chat?.delete_message ?? false)}
						{#if !compactPreview && !readOnly && allowDelete && (!isFirstMessage || siblings.length > 1)}
							<Tooltip content={$i18n.t('Delete')} placement="bottom">
								<button
									aria-label={$i18n.t('Delete')}
									class="{($settings?.highContrastMode ?? false)
										? ''
										: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
									on:click={(e) => {
										if (e.shiftKey) {
											deleteMessageHandler();
										} else {
											showDeleteConfirm = true;
										}
									}}
								>
									<TrashIcon />
								</button>
							</Tooltip>
						{/if}
					{/if}

					{#if !compactPreview && ($settings?.chatBubble ?? true) && isOwn}
						{#if siblings.length > 1}
							<div class="flex self-center" dir="ltr">
								<button
									aria-label={$i18n.t('Previous message')}
									class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
									on:click={() => {
										showPreviousMessage(message);
									}}
								>
									<ChevronRightIcon className="size-4 rotate-180" />
								</button>

								{#if messageIndexEdit}
									<div
										class="text-sm flex justify-center font-normal self-center dark:text-gray-500 min-w-fit"
									>
										<input
											id="message-index-input-{message.id}"
											type="number"
											value={siblings.indexOf(message.id) + 1}
											min="1"
											max={siblings.length}
											on:focus={(e) => {
												e.target.select();
											}}
											on:blur={(e) => {
												gotoMessage(message, e.target.value - 1);
												messageIndexEdit = false;
											}}
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}
											}}
											class="bg-transparent font-normal self-center dark:text-gray-500 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-normal self-center dark:text-gray-500 min-w-fit"
										on:dblclick={async () => {
											messageIndexEdit = true;

											await tick();
											const input = document.getElementById(`message-index-input-${message.id}`);
											if (input) {
												input.focus();
												input.select();
											}
										}}
									>
										{siblings.indexOf(message.id) + 1}/{siblings.length}
									</div>
								{/if}

								<button
									aria-label={$i18n.t('Next message')}
									class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
									on:click={() => {
										showNextMessage(message);
									}}
								>
									<ChevronRightIcon className="size-4" />
								</button>
							</div>
						{/if}
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
