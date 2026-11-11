<script lang="ts">
	import { getContext } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import { user } from '$lib/stores';
	import { createNewChat } from '$lib/apis/chats';
	import { refreshChatList, refreshFolderChatLists } from '$lib/stores/chatList';
	import { convertMessagesToHistory, isRasterImageContentType } from '$lib/utils';
	import Chat from '../Chat.svelte';

	export let initialPrompt = '';
	export let standalone = false;
	export let initialView: any = null;
	export const captureView = () => ({ draft, files, context });
	export let chatId = '';
	export let streaming = false;
	export let onChatUpdate: (chat: { id: string; title?: string }) => void = () => {};
	export let parentChatId = '';
	export let parentFolderId: string | null = null;
	export let history;
	export let modelId: string | null = null;
	export let systemPrompt = '';
	const i18n = getContext<any>('i18n');
	const originalChatId = parentChatId;
	const draftKey = uuidv4();
	const restored = !!initialView;
	let draft = initialView?.draft ?? initialPrompt;
	let files: any[] = initialView?.files ?? [];
	$: sideChatAllowed =
		$user?.role === 'admin' ||
		($user?.role === 'user' && (standalone || ($user.permissions?.chat?.side_chat ?? false)));
	// Snapshot the active branch once; later parent edits and streaming stay in the parent.
	let context = (() => {
		if (initialView?.context) return initialView.context;
		if (chatId || standalone) return [];
		const branch: any[] = [];
		let current = history?.currentId;
		const seen = new Set<string>();
		while (current && !seen.has(current) && history.messages[current]) {
			seen.add(current);
			const message = history.messages[current];
			branch.unshift(message);
			current = message.parentId;
		}
		while (branch.at(-1)?.role === 'assistant' && !branch.at(-1)?.done) branch.pop();
		return structuredClone(
			branch.map(
				(
					{ id, role, content, output, files, contextSummary, model, models, timestamp },
					index
				) => ({
					id,
					role,
					content: content ?? '',
					...(output?.length && role === 'assistant' ? { output } : {}),
					files,
					contextSummary,
					model,
					models,
					timestamp,
					done: true,
					parentId: branch[index - 1]?.id ?? null,
					childrenIds: branch[index + 1] ? [branch[index + 1].id] : []
				})
			)
		);
	})();
	const contextFiles = () =>
		context
			.flatMap((message: any) => message.files ?? [])
			.filter(
				(item: any) =>
					['doc', 'text', 'note', 'chat', 'folder', 'collection'].includes(item.type) ||
					(item.type === 'file' && !isRasterImageContentType(item?.content_type))
			);
	const embeddedDraft = {
		selectedModels: [modelId ?? ''],
		params: context.length
			? {
					system: [
						systemPrompt,
						'This is a separate side conversation. Earlier messages are reference context only. Answer the side question; do not continue the parent task.'
					]
						.filter(Boolean)
						.join('\n\n')
				}
			: {},
		history: convertMessagesToHistory(context),
		chatFiles: contextFiles(),
		temporary:
			!chatId &&
			$user?.role !== 'admin' &&
			($user?.permissions?.chat?.temporary ?? true) &&
			($user?.permissions?.chat?.temporary_enforced ?? false),
		prompt: draft,
		files
	};
	$: title = draft.trim().slice(0, 100) || $i18n.t('New Chat');

	const createChat = async (chat: {
		models: string[];
		params: Record<string, any>;
		variables: Record<string, any>;
	}) => {
		const created = await createNewChat(
			localStorage.token,
			{
				title,
				...(originalChatId && {
					originalChatId,
					branchPointMessageId: context.at(-1)?.id ?? null
				}),
				models: chat.models,
				params: chat.params,
				history: convertMessagesToHistory(context),
				messages: context,
				files: contextFiles(),
				tags: [],
				timestamp: Date.now()
			},
			parentFolderId,
			chat.variables
		);
		void refreshChatList(localStorage.token);
		if (created.folder_id) void refreshFolderChatLists(created.folder_id, created);
		return created;
	};
</script>

{#if sideChatAllowed}
	<Chat
		embedded={true}
		side={true}
		{parentChatId}
		chatIdProp={chatId}
		embeddedDraftKey={chatId ? '' : draftKey}
		embeddedDraft={restored || !chatId ? embeddedDraft : null}
		initialPrompt={restored ? '' : initialPrompt}
		bind:prompt={draft}
		bind:streaming
		bind:files
		onCreateEmbeddedChat={createChat}
		onSelectEmbeddedChat={(id) => onChatUpdate({ id, title })}
		onEmbeddedChatTitle={(id, chatTitle) => onChatUpdate({ id, title: chatTitle })}
	/>
{:else}
	<p role="status" class="px-4 py-2 text-xs text-gray-500">
		{$i18n.t('You do not have permission to use side chat.')}
	</p>
{/if}
