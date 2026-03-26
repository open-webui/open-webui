<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { getChatList } from '$lib/apis/chats';
	import { updateFolderById } from '$lib/apis/folders';

	import {
		config,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage
	} from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';

	const i18n = getContext('i18n');

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let onUpload: Function = (e) => {};
	export let onSelect = (e) => {};
	export let onChange = (e) => {};

	export let toolServers = [];
	export let pendingOAuthTools = [];

	export let dragged = false;
	let logoFailed = false;

	let models = [];
	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	onMount(() => {
		document.querySelector('.app > div')?.classList.add('copilot-landing-active-surface');

		return () => {
			document.querySelector('.app > div')?.classList.remove('copilot-landing-active-surface');
		};
	});
</script>

<div class="vx-page-bg landing-page-wrap w-full">
	<div class="copilot-landing-shell landing-shell mx-auto w-full text-center">
		{#if $temporaryChatEnabled}
			<Tooltip
				content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
				className="w-full flex justify-center mb-0.5"
				placement="top"
			>
				<div class="flex items-center gap-2 text-base my-2 w-fit landing-muted">
					<EyeSlash strokeWidth="2.5" className="size-4" />{$i18n.t('Temporary Chat')}
				</div>
			</Tooltip>
		{/if}

		<div class="landing-content text-center flex items-center gap-4 font-primary">
			<div class="w-full flex flex-col justify-center items-center">
				{#if $selectedFolder}
					<FolderTitle
						folder={$selectedFolder}
						onUpdate={async (folder) => {
							await chats.set(await getChatList(localStorage.token, $currentChatPage));
							currentChatPage.set(1);
						}}
						onDelete={async () => {
							await chats.set(await getChatList(localStorage.token, $currentChatPage));
							currentChatPage.set(1);

							selectedFolder.set(null);
						}}
					/>
				{:else}
					<div class="landing-brand" in:fade={{ duration: 100 }}>
						{#if !logoFailed}
							<img
								src="/venomx-logo.png"
								alt="VenomX logo"
								class="landing-logo"
								on:error={() => {
									logoFailed = true;
									console.warn('VenomX logo failed to load:', '/venomx-logo.png');
								}}
							/>
						{:else}
							<div class="landing-logo-fallback" aria-hidden="true">VX</div>
						{/if}
						<Tooltip content="VenomX" placement="top" className="flex items-center justify-center">
							<span class="line-clamp-1 landing-title">VenomX</span>
						</Tooltip>
					</div>

					<div class="landing-subheading" in:fade={{ duration: 100, delay: 40 }}>
						Local security assistant for triage, recon, and reporting.
					</div>

					<div class="flex mt-1 mb-2">
						<div in:fade={{ duration: 100, delay: 50 }}>
							{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
								<Tooltip
									className=" w-fit"
									content={marked.parse(
										sanitizeResponseContent(
											models[selectedModelIdx]?.info?.meta?.description ?? ''
										).replaceAll('\n', '<br>')
									)}
									placement="top"
								>
									<div
										class="landing-muted mt-0.5 px-2 text-sm font-normal line-clamp-2 max-w-xl markdown"
									>
										{@html marked.parse(
											sanitizeResponseContent(
												models[selectedModelIdx]?.info?.meta?.description ?? ''
											).replaceAll('\n', '<br>')
										)}
									</div>
								</Tooltip>

								{#if models[selectedModelIdx]?.info?.meta?.user}
									<div class="landing-muted mt-0.5 text-sm font-normal">
										By
										{#if models[selectedModelIdx]?.info?.meta?.user.community}
											<a
												href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
													.username}"
												>{models[selectedModelIdx]?.info?.meta?.user.name
													? models[selectedModelIdx]?.info?.meta?.user.name
													: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
											>
										{:else}
											{models[selectedModelIdx]?.info?.meta?.user.name}
										{/if}
									</div>
								{/if}
							{/if}
						</div>
					</div>
				{/if}

				{#if !$selectedFolder}
					<div class="vx-card landing-card" in:fade={{ duration: 180, delay: 120 }}>
						<div class="text-base font-normal w-full">
							<MessageInput
								bind:this={messageInput}
								{history}
								{selectedModels}
								bind:files
								bind:prompt
								bind:autoScroll
								bind:selectedToolIds
								bind:selectedFilterIds
								bind:imageGenerationEnabled
								bind:codeInterpreterEnabled
								bind:webSearchEnabled
								bind:atSelectedModel
								bind:showCommands
								bind:dragged
								{pendingOAuthTools}
								{toolServers}
								{stopResponse}
								{createMessagePair}
								placeholder={$i18n.t('How can I help you today?')}
								{onChange}
								{onUpload}
								on:submit={(e) => {
									dispatch('submit', e.detail);
								}}
							/>
						</div>

						<div class="w-full">
							<Suggestions
								chipMode={true}
								className="items-start"
								suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
									models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
									$config?.default_prompt_suggestions ??
									[]}
								inputValue={prompt}
								{onSelect}
							/>
						</div>

						<div class="landing-hint">Shift+Enter for newline • / for commands</div>
					</div>
				{/if}
			</div>
		</div>

		{#if $selectedFolder}
			<div
				class="mx-auto px-4 md:max-w-3xl md:px-6 font-primary min-h-62"
				in:fade={{ duration: 200, delay: 200 }}
			>
				<FolderPlaceholder folder={$selectedFolder} />
			</div>
		{/if}
	</div>
</div>

<style>
	.landing-page-wrap {
		min-height: 100dvh;
		box-sizing: border-box;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: clamp(1rem, 4vh, 2.5rem) 0;
	}

	.landing-shell {
		max-width: 980px;
		width: 100%;
		padding: clamp(2rem, 6vh, 4.5rem) 1rem clamp(1.25rem, 4vh, 3rem);
		transform: translateY(clamp(0.25rem, 1.3vh, 0.9rem));
	}

	.landing-content {
		color: var(--vx-text);
	}

	.landing-brand {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.45rem;
		margin-bottom: 0.4rem;
	}

	.landing-logo {
		width: 3rem;
		height: 3rem;
		object-fit: contain;
		filter: drop-shadow(0 1px 8px rgba(17, 34, 58, 0.16));
	}

	.landing-logo-fallback {
		width: 3rem;
		height: 3rem;
		border-radius: 999px;
		display: grid;
		place-items: center;
		font-size: 0.9rem;
		font-weight: 700;
		letter-spacing: 0.04em;
		color: var(--vx-text);
		background: rgba(255, 255, 255, 0.62);
		border: 1px solid rgba(22, 53, 88, 0.2);
	}

	.landing-title {
		color: var(--vx-text);
		font-size: clamp(2.05rem, 5vw, 2.75rem);
		line-height: 1.1;
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.landing-subheading {
		color: var(--vx-muted);
		font-size: clamp(0.9rem, 1.65vw, 1rem);
		font-weight: 500;
		line-height: 1.5;
		max-width: 38rem;
		margin-top: 0.35rem;
		padding: 0 0.75rem;
		text-wrap: balance;
	}

	.landing-card {
		width: 100%;
		max-width: 900px;
		margin-top: 0.85rem;
		padding: 0.85rem 0.9rem;
		background: rgba(250, 253, 255, 0.84);
		border: 1px solid rgba(22, 53, 88, 0.2);
		box-shadow:
			0 16px 34px rgba(7, 17, 32, 0.14),
			0 1px 0 rgba(255, 255, 255, 0.34) inset;
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.landing-card :global(#message-input-container) {
		min-height: 4.15rem;
		padding: 0.24rem !important;
		border-width: 1px !important;
		border-style: solid !important;
		border-radius: var(--vx-radius-md) !important;
		background: rgba(255, 255, 255, 0.88) !important;
		border-color: rgba(22, 53, 88, 0.2) !important;
		box-shadow:
			0 7px 18px rgba(11, 23, 40, 0.1),
			0 1px 0 rgba(255, 255, 255, 0.5) inset !important;
	}

	.landing-card
		:global(#message-input-container :is(svg, [class*='text-gray'], [class*='dark:text-gray'])) {
		color: var(--vx-text) !important;
	}

	.landing-card
		:global(#message-input-container :is([class*='stroke-gray'], [class*='dark:stroke-gray'])) {
		stroke: currentColor !important;
	}

	.landing-card
		:global(#message-input-container :is([class*='fill-gray'], [class*='dark:fill-gray'])) {
		fill: currentColor !important;
	}

	.landing-card
		:global(#message-input-container .ProseMirror p.is-editor-empty:first-child::before) {
		color: #1f2937 !important;
		opacity: 1 !important;
	}

	:global(html.dark)
		.landing-card
		:global(#message-input-container .ProseMirror p.is-editor-empty:first-child::before) {
		color: #e5e7eb !important;
		opacity: 1 !important;
	}

	.landing-card :global(#message-input-container button[aria-label='Voice mode'] svg) {
		color: inherit !important;
		stroke: currentColor !important;
	}

	.landing-muted {
		color: var(--vx-muted);
	}

	.landing-hint {
		color: var(--vx-muted);
		font-size: 0.75rem;
		line-height: 1.3;
		opacity: 0.9;
	}

	@media (min-width: 640px) {
		.landing-logo {
			width: 3.5rem;
			height: 3.5rem;
		}

		.landing-logo-fallback {
			width: 3.5rem;
			height: 3.5rem;
			font-size: 1rem;
		}

		.landing-shell {
			padding: clamp(2.5rem, 7vh, 5.25rem) 1.25rem clamp(1.75rem, 4.5vh, 3.5rem);
		}

		.landing-card {
			padding: 0.95rem 1rem;
			gap: 0.85rem;
		}
	}

	@media (max-height: 740px) {
		.landing-page-wrap {
			align-items: flex-start;
			padding-top: 1rem;
		}

		.landing-shell {
			transform: none;
		}
	}

	:global(html.dark) .landing-card {
		background: rgba(18, 33, 53, 0.82);
		border-color: rgba(145, 171, 198, 0.24);
		box-shadow:
			0 18px 36px rgba(2, 8, 17, 0.36),
			0 1px 0 rgba(225, 238, 255, 0.08) inset;
	}

	:global(html.dark) .landing-card :global(#message-input-container) {
		background: rgba(31, 49, 74, 0.92) !important;
		border-color: rgba(161, 187, 214, 0.26) !important;
		box-shadow:
			0 8px 22px rgba(1, 7, 16, 0.38),
			0 1px 0 rgba(223, 238, 255, 0.08) inset !important;
	}
</style>
