<script lang="ts">
	import dayjs from 'dayjs';

	import { tick, createEventDispatcher, getContext } from 'svelte';
	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import { modelfiles, settings } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { user as _user } from '$lib/stores';

	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	export let user;
	export let message;
	export let siblings;
	export let isFirstMessage: boolean;
	export let readOnly: boolean;

	export let confirmEditMessage: Function;
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;
	export let copyToClipboard: Function;

	let edit = false;
	let editedContent = '';
	let messageEditTextAreaElement: HTMLTextAreaElement;
	const editMessageHandler = async () => {
		edit = true;
		editedContent = message.content;

		await tick();

		messageEditTextAreaElement.style.height = '';
		messageEditTextAreaElement.style.height = `${messageEditTextAreaElement.scrollHeight}px`;

		messageEditTextAreaElement?.focus();
	};

	const editMessageConfirmHandler = async () => {
		confirmEditMessage(message.id, editedContent);

		edit = false;
		editedContent = '';
	};

	const cancelEditMessage = () => {
		edit = false;
		editedContent = '';
	};

	const deleteMessageHandler = async () => {
		dispatch('delete', message.id);
	};
</script>

<div class=" flex w-full user-message" dir={$settings.chatDirection}>
	{#if !($settings?.chatBubble ?? true)}
		<ProfileImage
			src={message.user
				? $modelfiles.find((modelfile) => modelfile.tagName === message.user)?.imageUrl ??
				  '/user.png'
				: user?.profile_image_url ?? '/user.png'}
		/>
	{/if}
	<div class="w-full overflow-hidden pl-1">
		{#if !($settings?.chatBubble ?? true)}
			<div>
				<Name>
					{#if message.user}
						{#if $modelfiles.map((modelfile) => modelfile.tagName).includes(message.user)}
							{$modelfiles.find((modelfile) => modelfile.tagName === message.user)?.title}
						{:else}
							{$i18n.t('You')}
							<span class=" text-gray-500 text-sm font-medium">{message?.user ?? ''}</span>
						{/if}
					{:else if $settings.showUsername || $_user.name !== user.name}
						{user.name}
					{:else}
						{$i18n.t('You')}
					{/if}

					{#if message.timestamp}
						<span
							class=" invisible group-hover:visible text-gray-400 text-xs font-medium uppercase"
						>
							{dayjs(message.timestamp * 1000).format($i18n.t('h:mm a'))}
						</span>
					{/if}
				</Name>
			</div>
		{/if}

		<div
			class="prose chat-{message.role} w-full max-w-full flex flex-col justify-end dark:prose-invert prose-headings:my-0 prose-p:my-0 prose-p:-mb-4 prose-pre:my-0 prose-table:my-0 prose-blockquote:my-0 prose-img:my-0 prose-ul:-my-4 prose-ol:-my-4 prose-li:-my-3 prose-ul:-mb-6 prose-ol:-mb-6 prose-li:-mb-4 whitespace-pre-line"
		>
			{#if message.files}
				<div class="mt-2.5 mb-1 w-full flex flex-col justify-end overflow-x-auto gap-1 flex-wrap">
					{#each message.files as file}
						<div class={$settings?.chatBubble ?? true ? 'self-end' : ''}>
							{#if file.type === 'image'}
								<img src={file.url} alt="input" class=" max-h-96 rounded-lg" draggable="false" />
							{:else if file.type === 'doc'}
								<button
									class="h-16 w-72 flex items-center space-x-3 px-2.5 dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-none text-left"
									type="button"
									on:click={() => {
										if (file?.url) {
											window.open(file?.url, '_blank').focus();
										}
									}}
								>
									<div class="p-2.5 bg-red-400 text-white rounded-lg">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="w-6 h-6"
										>
											<path
												fill-rule="evenodd"
												d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
												clip-rule="evenodd"
											/>
											<path
												d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
											/>
										</svg>
									</div>

									<div class="flex flex-col justify-center -space-y-0.5">
										<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1">
											{file.name}
										</div>

										<div class=" text-gray-500 text-sm">{$i18n.t('Document')}</div>
									</div>
								</button>
							{:else if file.type === 'collection'}
								<button
									class="h-16 w-72 flex items-center space-x-3 px-2.5 dark:bg-gray-600 rounded-xl border border-gray-200 dark:border-none text-left"
									type="button"
								>
									<div class="p-2.5 bg-red-400 text-white rounded-lg">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="w-6 h-6"
										>
											<path
												d="M7.5 3.375c0-1.036.84-1.875 1.875-1.875h.375a3.75 3.75 0 0 1 3.75 3.75v1.875C13.5 8.161 14.34 9 15.375 9h1.875A3.75 3.75 0 0 1 21 12.75v3.375C21 17.16 20.16 18 19.125 18h-9.75A1.875 1.875 0 0 1 7.5 16.125V3.375Z"
											/>
											<path
												d="M15 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 17.25 7.5h-1.875A.375.375 0 0 1 15 7.125V5.25ZM4.875 6H6v10.125A3.375 3.375 0 0 0 9.375 19.5H16.5v1.125c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 0 1 3 20.625V7.875C3 6.839 3.84 6 4.875 6Z"
											/>
										</svg>
									</div>

									<div class="flex flex-col justify-center -space-y-0.5">
										<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1">
											{file?.title ?? `#${file.name}`}
										</div>

										<div class=" text-gray-500 text-sm">{$i18n.t('Collection')}</div>
									</div>
								</button>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if edit === true}
				<div class=" w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 mb-2">
					<textarea
						id="message-edit-{message.id}"
						bind:this={messageEditTextAreaElement}
						class=" bg-transparent outline-none w-full resize-none"
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
								document.getElementById('save-edit-message-button')?.click();
							}
						}}
					/>

					<div class=" mt-2 mb-1 flex justify-end space-x-1.5 text-sm font-medium">
						<button
							id="close-edit-message-button"
							class="px-4 py-2 bg-white hover:bg-gray-100 text-gray-800 transition rounded-3xl"
							on:click={() => {
								cancelEditMessage();
							}}
						>
							{$i18n.t('Cancel')}
						</button>

						<button
							id="save-edit-message-button"
							class=" px-4 py-2 bg-gray-900 hover:bg-gray-850 text-gray-100 transition rounded-3xl"
							on:click={() => {
								editMessageConfirmHandler();
							}}
						>
							{$i18n.t('Send')}
						</button>
					</div>
				</div>
			{:else}
				<div class="w-full">
					<div class="flex {$settings?.chatBubble ?? true ? 'justify-end' : ''} mb-2">
						<div
							class="rounded-3xl {$settings?.chatBubble ?? true
								? `max-w-[90%] px-5 py-2  bg-gray-50 dark:bg-gray-850 ${
										message.files ? 'rounded-tr-lg' : ''
								  }`
								: ''}  "
						>
							<pre id="user-message">{message.content}</pre>
						</div>
					</div>

					<div
						class=" flex {$settings?.chatBubble ?? true
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

									<div class="text-sm tracking-widest font-semibold self-center dark:text-gray-100">
										{siblings.indexOf(message.id) + 1}/{siblings.length}
									</div>

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
									class="invisible group-hover:visible p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition edit-user-message-button"
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

						<Tooltip content={$i18n.t('Copy')} placement="bottom">
							<button
								class="invisible group-hover:visible p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
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

						{#if !isFirstMessage && !readOnly}
							<Tooltip content={$i18n.t('Delete')} placement="bottom">
								<button
									class="invisible group-hover:visible p-1 rounded dark:hover:text-white hover:text-black transition"
									on:click={() => {
										deleteMessageHandler();
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

									<div class="text-sm tracking-widest font-semibold self-center dark:text-gray-100">
										{siblings.indexOf(message.id) + 1}/{siblings.length}
									</div>

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
		</div>
	</div>
</div>
