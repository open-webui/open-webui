<script lang="ts">
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount } from 'svelte';

	import { models, settings } from '$lib/stores';
	import { user as _user } from '$lib/stores';
	import { copyToClipboard as _copyToClipboard, formatDate } from '$lib/utils';

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

	let showDeleteConfirm = false;

	let messageIndexEdit = false;

	let edit = false;
	let editedContent = '';
	let editedFiles = [];

	let messageEditTextAreaElement: HTMLTextAreaElement;

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
		editedContent = message.content;
		editedFiles = message.files;

		await tick();

		if (messageEditTextAreaElement) {
			messageEditTextAreaElement.style.height = '';
			messageEditTextAreaElement.style.height = `${messageEditTextAreaElement.scrollHeight}px`;

			messageEditTextAreaElement?.focus();
		}
	};

	const editMessageConfirmHandler = async (submit = true) => {
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
		<div class={`shrink-0 ltr:mr-3 rtl:ml-3`}>
			<ProfileImage
				src={message.user
					? ($models.find((m) => m.id === message.user)?.info?.meta?.profile_image_url ??
						'/user.png')
					: (user?.profile_image_url ?? '/user.png')}
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
							class=" self-center text-xs invisible text-gray-400 font-medium first-letter:capitalize ml-0.5 translate-y-[1px]"
						>
							<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
								<span class="line-clamp-1">{formatDate(message.timestamp * 1000)}</span>
							</Tooltip>
						</div>
					{/if}
				</Name>
			</div>
		{:else if message.timestamp}
			<div class="flex justify-end pb-1 pr-2">
				<div
					class="text-xs invisible text-gray-400 font-medium first-letter:capitalize translate-y-[1px]"
				>
					<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
						<span class="line-clamp-1">{formatDate(message.timestamp * 1000)}</span>
					</Tooltip>
				</div>
			</div>
		{/if}

		<div class="chat-{message.role} w-full min-w-full markdown-prose">
			{#if edit !== true}
				{#if message.files}
					<div class="mt-2.5 mb-1 w-full flex flex-col justify-end overflow-x-auto gap-1 flex-wrap">
						{#each message.files as file}
							<div class={($settings?.chatBubble ?? true) ? 'self-end' : ''}>
								{#if file.type === 'image'}
									<Image src={file.url} imageClassName=" max-h-96 rounded-lg" />
								{:else}
									<FileItem
										item={file}
										url={file.url}
										name={file.name}
										type={file.type}
										size={file?.size}
										colorClassName="bg-white dark:bg-gray-850 "
									/>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			{/if}

			{#if message.content !== ''}
				{#if edit === true}
					<div class="w-full bg-light-bg rounded-[12px] p-[24px] mb-[8px] shadow-custom4">
						{#if (editedFiles ?? []).length > 0}
							<div class="flex items-center flex-wrap gap-2 -mx-2 mb-1">
								{#each editedFiles as file, fileIdx}
									{#if file.type === 'image'}
										<div class=" relative group">
											<div class="relative flex items-center">
												<Image
													src={file.url}
													alt="input"
													imageClassName=" size-14 rounded-xl object-cover"
												/>
											</div>
											<div class=" absolute -top-1 -right-1">
												<button
													class=" bg-white text-black border border-white rounded-full group-hover:visible invisible transition"
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

						<div class="max-h-96 overflow-auto">
							<textarea
								id="message-edit-{message.id}"
								bind:this={messageEditTextAreaElement}
								class=" bg-transparent outline-hidden w-full resize-none"
								bind:value={editedContent}
								on:input={(e) => {
									e.target.style.height = '';
									e.target.style.height = `${e.target.scrollHeight}px`;
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

						<div class="mt-[20px] flex justify-between text-sm font-medium">
							<div>
								<button
									id="save-edit-message-button"
									class=" btn-primary"
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
									class="btn-secondary"
									on:click={() => {
										cancelEditMessage();
									}}
								>
									{$i18n.t('Cancel')}
								</button>

								<button
									id="confirm-edit-message-button"
									class="btn-primary"
									on:click={() => {
										editMessageConfirmHandler();
									}}
								>
									{$i18n.t('Send')}
								</button>
							</div>
						</div>
					</div>
				{:else}
					<div class="w-full">
						<div class="flex {($settings?.chatBubble ?? true) ? 'justify-end pb-1' : 'w-full'}">
							<div
								class="rounded-[16px] text-[14px] text-typography-titles leading-[24px] {($settings?.chatBubble ??
								true)
									? `max-w-[90%] p-[24px] bg-light-bg shadow-custom4 ${
											message.files ? 'rounded-tr-lg' : ''
										}`
									: ' w-full'}"
							>
								{#if message.content}
									<Markdown id={message.id} content={message.content} />
								{/if}
							</div>
						</div>

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
													const input = document.getElementById(
														`message-index-input-${message.id}`
													);
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
										class=" p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition edit-user-message-button"
										on:click={() => {
											editMessageHandler();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="18"
											height="18"
											viewBox="0 0 18 18"
											fill="none"
										>
											<mask
												id="mask0_2146_3836"
												style="mask-type:alpha"
												maskUnits="userSpaceOnUse"
												x="0"
												y="0"
												width="18"
												height="18"
											>
												<rect width="18" height="18" fill="#D9D9D9" />
											</mask>
											<g mask="url(#mask0_2146_3836)">
												<path
													d="M3.44803 15.3469C3.20965 15.3998 3.0044 15.3402 2.83228 15.168C2.66015 14.9959 2.60053 14.7907 2.6534 14.5523L3.28078 11.5407L6.45965 14.7195L3.44803 15.3469ZM6.45965 14.7195L3.28078 11.5407L11.6952 3.12622C11.9538 2.86759 12.274 2.73828 12.6558 2.73828C13.0375 2.73828 13.3577 2.86759 13.6163 3.12622L14.8741 4.38397C15.1327 4.64259 15.262 4.96278 15.262 5.34453C15.262 5.72628 15.1327 6.04647 14.8741 6.30509L6.45965 14.7195ZM12.4972 3.91672L4.8284 11.5782L6.42215 13.1719L14.0836 5.50316C14.1268 5.45991 14.1485 5.40584 14.1485 5.34097C14.1485 5.27597 14.1268 5.22184 14.0836 5.17859L12.8217 3.91672C12.7785 3.87347 12.7243 3.85184 12.6593 3.85184C12.5945 3.85184 12.5404 3.87347 12.4972 3.91672Z"
													fill="#23282E"
												/>
											</g>
										</svg>
									</button>
								</Tooltip>
							{/if}

							<Tooltip content={$i18n.t('Copy')} placement="bottom">
								<button
									class=" p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
									on:click={() => {
										copyToClipboard(message.content);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="18"
										height="18"
										viewBox="0 0 18 18"
										fill="none"
									>
										<path
											d="M6.79331 13.125C6.41444 13.125 6.09375 12.9938 5.83125 12.7313C5.56875 12.4688 5.4375 12.1481 5.4375 11.7692V3.23081C5.4375 2.85194 5.56875 2.53125 5.83125 2.26875C6.09375 2.00625 6.41444 1.875 6.79331 1.875H13.0817C13.4606 1.875 13.7812 2.00625 14.0438 2.26875C14.3063 2.53125 14.4375 2.85194 14.4375 3.23081V11.7692C14.4375 12.1481 14.3063 12.4688 14.0438 12.7313C13.7812 12.9938 13.4606 13.125 13.0817 13.125H6.79331ZM6.79331 12H13.0817C13.1394 12 13.1923 11.9759 13.2403 11.9278C13.2884 11.8798 13.3125 11.8269 13.3125 11.7692V3.23081C13.3125 3.17306 13.2884 3.12019 13.2403 3.07219C13.1923 3.02406 13.1394 3 13.0817 3H6.79331C6.73556 3 6.68269 3.02406 6.63469 3.07219C6.58656 3.12019 6.5625 3.17306 6.5625 3.23081V11.7692C6.5625 11.8269 6.58656 11.8798 6.63469 11.9278C6.68269 11.9759 6.73556 12 6.79331 12ZM4.16831 15.75C3.78944 15.75 3.46875 15.6188 3.20625 15.3563C2.94375 15.0938 2.8125 14.7731 2.8125 14.3942V4.73081H3.9375V14.3942C3.9375 14.4519 3.96156 14.5048 4.00969 14.5528C4.05769 14.6009 4.11056 14.625 4.16831 14.625H11.5817V15.75H4.16831Z"
											fill="#23282E"
										/>
									</svg>
								</button>
							</Tooltip>

							{#if !readOnly && (!isFirstMessage || siblings.length > 1)}
								<Tooltip content={$i18n.t('Delete')} placement="bottom">
									<button
										class=" p-1 rounded-sm dark:hover:text-white hover:text-black transition"
										on:click={() => {
											showDeleteConfirm = true;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="18"
											height="18"
											viewBox="0 0 18 18"
											fill="none"
										>
											<mask
												id="mask0_2146_3844"
												style="mask-type:alpha"
												maskUnits="userSpaceOnUse"
												x="0"
												y="0"
												width="18"
												height="18"
											>
												<rect width="18" height="18" fill="#D9D9D9" />
											</mask>
											<g mask="url(#mask0_2146_3844)">
												<path
													d="M5.48081 15.3743C5.10681 15.3743 4.78731 15.2419 4.52231 14.977C4.25744 14.712 4.125 14.3925 4.125 14.0185V4.49931H3.375V3.37431H6.75V2.71094H11.25V3.37431H14.625V4.49931H13.875V14.0185C13.875 14.3974 13.7438 14.7181 13.4813 14.9806C13.2188 15.2431 12.8981 15.3743 12.5192 15.3743H5.48081ZM12.75 4.49931H5.25V14.0185C5.25 14.0859 5.27162 14.1412 5.31487 14.1844C5.35812 14.2277 5.41344 14.2493 5.48081 14.2493H12.5192C12.5769 14.2493 12.6298 14.2253 12.6778 14.1771C12.7259 14.1291 12.75 14.0763 12.75 14.0185V4.49931ZM7.053 12.7493H8.17781V5.99931H7.053V12.7493ZM9.82219 12.7493H10.947V5.99931H9.82219V12.7493Z"
													fill="#23282E"
												/>
											</g>
										</svg>
									</button>
								</Tooltip>
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
													const input = document.getElementById(
														`message-index-input-${message.id}`
													);
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
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
