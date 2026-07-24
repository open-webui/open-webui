<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount } from 'svelte';

	import { models, settings } from '$lib/stores';
	import { user as _user } from '$lib/stores';
	import {
		copyToClipboard as _copyToClipboard,
		formatMessageTimestamp,
		formatMessageTimestampFull
	} from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import equal from 'fast-deep-equal';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Markdown from './Markdown.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import SubagentResultRow from './SubagentResultRow.svelte';

	const i18n = getContext('i18n');
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
		editedFiles = message.files;

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
	class=" flex w-full user-message group"
	dir={$settings.chatDirection}
	id="message-{message.id}"
	style="scroll-margin-top: 3rem;"
>
	{#if !($settings?.chatBubble ?? true) && !(message?.meta?.internal === true && message?.meta?.type === 'subagent') && !(message?.meta?.internal === true && message?.meta?.type === 'timer')}
		<div class={`shrink-0 ltr:mr-2 rtl:ml-2 hidden @lg:flex mt-0.5`}>
			<ProfileImage
				src={user?.id
					? `${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`
					: `${WEBUI_BASE_URL}/static/favicon.png`}
				className={'size-7 user-message-profile-image'}
			/>
		</div>
	{/if}
	<div
		class="flex-auto w-0 max-w-full {(message?.meta?.internal === true &&
			message?.meta?.type === 'subagent') ||
		(message?.meta?.internal === true && message?.meta?.type === 'timer')
			? ''
			: 'pl-1'}"
	>
		{#if !($settings?.chatBubble ?? true) && !(message?.meta?.internal === true && message?.meta?.type === 'subagent') && !(message?.meta?.internal === true && message?.meta?.type === 'timer')}
			<div>
				<Name>
					{#if message.user}
						{$i18n.t('You')}
						<span class=" text-gray-500 text-[0.9375rem] font-normal">{message?.user ?? ''}</span>
					{:else if $settings.showUsername || $_user?.name !== user?.name}
						{user?.name ?? $i18n.t('You')}
					{:else}
						{$i18n.t('You')}
					{/if}
				</Name>
			</div>
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
							<div class={($settings?.chatBubble ?? true) ? 'self-end' : ''}>
								{#if file.type === 'image' || (file?.content_type ?? '').startsWith('image/')}
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
				<div class=" w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-4 py-3 mb-2">
					{#if (editedFiles ?? []).length > 0}
						<div class="flex items-center flex-wrap gap-2 -mx-2 mb-1">
							{#each editedFiles as file, fileIdx}
								{#if file.type === 'image' || (file?.content_type ?? '').startsWith('image/')}
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
												class=" bg-white text-black border border-white rounded-full {($settings?.highContrastMode ??
												false)
													? ''
													: 'group-hover:visible invisible transition'}"
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
							class=" bg-transparent outline-hidden w-full resize-none text-[0.9375rem]"
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
							<button
								id="save-edit-message-button"
								class="px-2.5 py-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
								on:click={() => {
									editMessageConfirmHandler(false);
								}}
							>
								{$i18n.t('Save')}
							</button>
						</div>

						<div class="flex space-x-1.5">
							<button
								id="close-edit-message-button"
								class="px-2.5 py-1 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
								on:click={() => {
									cancelEditMessage();
								}}
							>
								{$i18n.t('Cancel')}
							</button>

							<button
								id="confirm-edit-message-button"
								class="px-2.5 py-1 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
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
					<div class="flex {($settings?.chatBubble ?? true) ? 'justify-end pb-1' : 'w-full'}">
						<div
							class="rounded-3xl {($settings?.chatBubble ?? true)
								? `max-w-[90%] px-4 py-1.5  bg-gray-50 dark:bg-gray-850 ${
										message.files ? 'rounded-tr-lg' : ''
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
					class=" flex {($settings?.chatBubble ?? true)
						? 'justify-end'
						: 'items-center'}  text-gray-600 dark:text-gray-500"
				>
					{#if message.timestamp}
						<Tooltip
							className="flex self-center {($settings?.chatBubble ?? true) ? 'mr-1' : 'order-last'}"
							content={formatMessageTimestampFull(message.timestamp * 1000)}
							placement="bottom"
						>
							<time
								datetime={new Date(message.timestamp * 1000).toISOString()}
								class="{compactPreview
									? ''
									: 'invisible group-hover:visible'} {($settings?.chatBubble ?? true)
									? 'mr-1'
									: 'ml-1 shrink-0 whitespace-nowrap'} text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-600 select-none"
							>
								{formatMessageTimestamp(message.timestamp * 1000)}
							</time>
						</Tooltip>
					{/if}

					{#if !compactPreview && !($settings?.chatBubble ?? true)}
						{#if siblings.length > 1}
							<div class="flex self-center" dir="ltr">
								<button
									class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
									on:click={() => {
										showPreviousMessage(message);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										stroke-width="2.5"
										class="size-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.75 19.5 8.25 12l7.5-7.5"
										/>
									</svg>
								</button>

								{#if messageIndexEdit}
									<div
										class="text-sm flex justify-center font-normal self-center dark:text-gray-100 min-w-fit"
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
											class="bg-transparent font-normal self-center dark:text-gray-100 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-normal self-center dark:text-gray-100 min-w-fit"
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
									class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
									on:click={() => {
										showNextMessage(message);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										stroke-width="2.5"
										class="size-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m8.25 4.5 7.5 7.5-7.5 7.5"
										/>
									</svg>
								</button>
							</div>
						{/if}
					{/if}
					{#if !compactPreview && !readOnly}
						<Tooltip content={$i18n.t('Edit')} placement="bottom">
							<button
								class="{($settings?.highContrastMode ?? false)
									? ''
									: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition edit-user-message-button"
								on:click={() => {
									editMessageHandler();
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2.3"
									stroke="currentColor"
									class="w-4 h-4"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
									/>
								</svg>
							</button>
						</Tooltip>
					{/if}

					{#if !compactPreview && message?.content}
						<Tooltip content={$i18n.t('Copy')} placement="bottom">
							<button
								class="{($settings?.highContrastMode ?? false)
									? ''
									: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
								on:click={() => {
									copyToClipboard(message.content);
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2.3"
									stroke="currentColor"
									class="w-4 h-4"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
									/>
								</svg>
							</button>
						</Tooltip>
					{/if}

					{#if $_user?.role === 'admin' || ($_user?.permissions?.chat?.delete_message ?? false)}
						{#if !compactPreview && !readOnly && allowDelete && (!isFirstMessage || siblings.length > 1)}
							<Tooltip content={$i18n.t('Delete')} placement="bottom">
								<button
									class="{($settings?.highContrastMode ?? false)
										? ''
										: 'invisible group-hover:visible'} p-1 rounded-sm dark:hover:text-white hover:text-black transition"
									on:click={(e) => {
										if (e.shiftKey) {
											deleteMessageHandler();
										} else {
											showDeleteConfirm = true;
										}
									}}
								>
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
											d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
										/>
									</svg>
								</button>
							</Tooltip>
						{/if}
					{/if}

					{#if !compactPreview && ($settings?.chatBubble ?? true)}
						{#if siblings.length > 1}
							<div class="flex self-center" dir="ltr">
								<button
									class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
									on:click={() => {
										showPreviousMessage(message);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										stroke-width="2.5"
										class="size-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.75 19.5 8.25 12l7.5-7.5"
										/>
									</svg>
								</button>

								{#if messageIndexEdit}
									<div
										class="text-sm flex justify-center font-normal self-center dark:text-gray-100 min-w-fit"
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
											class="bg-transparent font-normal self-center dark:text-gray-100 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-normal self-center dark:text-gray-100 min-w-fit"
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
									class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
									on:click={() => {
										showNextMessage(message);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										stroke-width="2.5"
										class="size-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m8.25 4.5 7.5 7.5-7.5 7.5"
										/>
									</svg>
								</button>
							</div>
						{/if}
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
