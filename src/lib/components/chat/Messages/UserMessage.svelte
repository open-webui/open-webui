<script lang="ts">
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount } from 'svelte';

	import { models, settings } from '$lib/stores';
	import { user as _user } from '$lib/stores';
	import { copyToClipboard as _copyToClipboard, formatDate } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Markdown from './Markdown.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import localizedFormat from 'dayjs/plugin/localizedFormat';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

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
	export let editCodeBlock = true;
	export let topPadding = false;

	let showDeleteConfirm = false;

	let messageIndexEdit = false;

	let edit = false;
	let editedContent = '';
	let editedFiles = [];

	let messageEditTextAreaElement: HTMLTextAreaElement;
	let editScrollContainer: HTMLDivElement;

	let message = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
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
>
	{#if !($settings?.chatBubble ?? true)}
		<div class={`shrink-0 ltr:mr-3 rtl:ml-3 mt-1`}>
			<ProfileImage
				src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
				className={'size-8 user-message-profile-image'}
			/>
		</div>
	{/if}
	<div class="flex-auto w-0 max-w-full pl-1">
		{#if !($settings?.chatBubble ?? true)}
			<div>
				<Name>
					{#if message.user}
						{$i18n.t('You')}
						<span class=" text-gray-500 text-sm font-medium">{message?.user ?? ''}</span>
					{:else if $settings.showUsername || $_user.name !== user.name}
						{user.name}
					{:else}
						{$i18n.t('You')}
					{/if}

					{#if message.timestamp}
						<div
							class="self-center text-xs font-medium first-letter:capitalize ml-0.5 translate-y-[1px] {($settings?.highContrastMode ??
							false)
								? 'dark:text-gray-900 text-gray-100'
								: 'invisible group-hover:visible transition'}"
						>
							<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
								<!-- $i18n.t('Today at {{LOCALIZED_TIME}}') -->
								<!-- $i18n.t('Yesterday at {{LOCALIZED_TIME}}') -->
								<!-- $i18n.t('{{LOCALIZED_DATE}} at {{LOCALIZED_TIME}}') -->

								<span class="line-clamp-1"
									>{$i18n.t(formatDate(message.timestamp * 1000), {
										LOCALIZED_TIME: dayjs(message.timestamp * 1000).format('LT'),
										LOCALIZED_DATE: dayjs(message.timestamp * 1000).format('L')
									})}</span
								>
							</Tooltip>
						</div>
					{/if}
				</Name>
			</div>
		{:else if message.timestamp}
			<div class="flex justify-end pr-2 text-xs">
				<div
					class="text-[0.65rem] font-medium first-letter:capitalize mb-0.5 {($settings?.highContrastMode ??
					false)
						? 'dark:text-gray-100 text-gray-900'
						: 'invisible group-hover:visible transition text-gray-400'}"
				>
					<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
						<span class="line-clamp-1"
							>{$i18n.t(formatDate(message.timestamp * 1000), {
								LOCALIZED_TIME: dayjs(message.timestamp * 1000).format('LT'),
								LOCALIZED_DATE: dayjs(message.timestamp * 1000).format('L')
							})}</span
						>
					</Tooltip>
				</div>
			</div>
		{/if}

		<div class="chat-{message.role} w-full min-w-full markdown-prose">
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
				<div class=" w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 mb-2">
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
							class=" bg-transparent outline-hidden w-full resize-none"
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

					<div class=" mt-2 mb-1 flex justify-between text-sm font-medium">
						<div>
							<button
								id="save-edit-message-button"
								class="px-3.5 py-1.5 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
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
								class="px-3.5 py-1.5 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
								on:click={() => {
									cancelEditMessage();
								}}
							>
								{$i18n.t('Cancel')}
							</button>

							<button
								id="confirm-edit-message-button"
								class="px-3.5 py-1.5 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
								on:click={() => {
									editMessageConfirmHandler();
								}}
							>
								{$i18n.t('Send')}
							</button>
						</div>
					</div>
				</div>
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
								<Markdown
									id={`${chatId}-${message.id}`}
									content={message.content}
									{editCodeBlock}
									{topPadding}
								/>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			{#if edit !== true}
				<div
					class=" flex {($settings?.chatBubble ?? true)
						? 'justify-end'
						: ''}  text-gray-600 dark:text-gray-500"
				>
					{#if !($settings?.chatBubble ?? true)}
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
										class="text-sm flex justify-center font-semibold self-center dark:text-gray-100 min-w-fit"
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
											class="bg-transparent font-semibold self-center dark:text-gray-100 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-semibold self-center dark:text-gray-100 min-w-fit"
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
					{#if !readOnly}
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

					{#if message?.content}
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
						{#if !readOnly && (!isFirstMessage || siblings.length > 1)}
							<Tooltip content={$i18n.t('Delete')} placement="bottom">
								<button
									class="{($settings?.highContrastMode ?? false)
										? ''
										: 'invisible group-hover:visible'} p-1 rounded-sm dark:hover:text-white hover:text-black transition"
									on:click={() => {
										showDeleteConfirm = true;
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

					{#if $settings?.chatBubble ?? true}
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
										class="text-sm flex justify-center font-semibold self-center dark:text-gray-100 min-w-fit"
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
											class="bg-transparent font-semibold self-center dark:text-gray-100 min-w-fit outline-hidden"
										/>/{siblings.length}
									</div>
								{:else}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<div
										class="text-sm tracking-widest font-semibold self-center dark:text-gray-100 min-w-fit"
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
