<script lang="ts">
	import { resolveToolApprovalMode } from '$lib/utils/toolPermissions';
	import { getContext, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import {
		socket,
		user,
		openSideChatIds,
		tags,
		models,
		settings,
		config,
		toolServers,
		terminalServers,
		tools,
		skills,
		selectedTerminalId,
		type Model
	} from '$lib/stores';
	import { createTemporaryChatId } from '$lib/utils/chatId';
	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { generateOpenAIChatCompletion, getErrorMessage } from '$lib/apis/openai';
	import { getTaskIdsByChatId, resumeTemporaryChat, stopTasksByChatId } from '$lib/apis';
	import {
		createNewChat,
		getAllTags,
		getChatById,
		resolveChatMessageToolCall,
		updateChatById
	} from '$lib/apis/chats';
	import { refreshChatList, refreshFolderChatLists } from '$lib/stores/chatList';
	import {
		applyResponseStreamEvent,
		getPendingAskUserFromMessage
	} from '../Messages/structuredOutput';
	import Messages from '../Messages.svelte';
	import MessageInput from '../MessageInput.svelte';
	import FilesOverlay from '../MessageInput/FilesOverlay.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ElicitationDialog from '../ElicitationDialog.svelte';
	import {
		convertMessagesToHistory,
		createMessagesList,
		isRasterImageContentType
	} from '$lib/utils';

	export let initialPrompt = '';
	export let initialView: any = null;
	export const captureView = () => ({ draft, files, context });
	export let chatId = '';
	export let onChatUpdate: (chat: { id: string; title?: string }) => void = () => {};
	export let parentChatId = '';
	export let parentFolderId: string | null = null;
	export let history;
	export let modelId: string;
	export let systemPrompt = '';
	const i18n = getContext<any>('i18n');
	let dragged = false;
	const originalChatId = parentChatId;
	$: sideChatAllowed =
		$user?.role === 'admin' ||
		($user?.role === 'user' && ($user.permissions?.chat?.side_chat ?? false));
	// Snapshot the active branch once; later parent edits and streaming stay in the parent.
	const context = (() => {
		if (initialView?.context) return initialView.context;
		if (chatId) return [];
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
	const contextIds = new Set(context.map((message) => message.id));
	let loaded = !chatId;
	let isShared = false;
	let readOnly = false;
	let temporary =
		!chatId && $user?.role !== 'admin' && ($user?.permissions?.chat?.temporary_enforced ?? false);
	$: canUseTemporary = $user?.role === 'admin' || ($user?.permissions?.chat?.temporary ?? true);
	$: canSave = $user?.role === 'admin' || !($user?.permissions?.chat?.temporary_enforced ?? false);
	$: canSend = loaded && !readOnly && sideChatAllowed && (temporary ? canUseTemporary : canSave);
	let selectedModels = [modelId];
	let atSelectedModel: Model | undefined = undefined;
	$: sideModelId = atSelectedModel?.id ?? selectedModels[0];
	let files: any[] = initialView?.files ?? [];
	let params: Record<string, any> = { ...$settings.params };
	let selectedToolIds: string[] = [];
	let selectedSkillIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let webSearchEnabled = false;
	let imageGenerationEnabled = false;
	let codeInterpreterEnabled = false;

	const applyModelDefaults = async (selectedModelId: string) => {
		if (!$tools) tools.set(await getTools(localStorage.token));
		if (!$skills) skills.set(await getSkills(localStorage.token));
		const selectedModel = $models.find((model) => model.id === selectedModelId);
		if (!selectedModel || $tools === null || $skills === null) return;
		if (id || selectedModelId !== sideModelId) return;
		const meta = selectedModel.info?.meta;
		const defaultFeature = (feature: 'web_search' | 'image_generation' | 'code_interpreter') =>
			!!meta?.defaultFeatureIds?.includes(feature) &&
			(meta?.capabilities?.[feature] ?? true) &&
			!!$config?.features?.[`enable_${feature}`] &&
			($user?.role === 'admin' || !!$user?.permissions?.features?.[feature]);
		selectedToolIds =
			meta?.toolIds?.filter((toolId: string) =>
				($tools as any[]).some((tool) => tool.id === toolId && tool.authenticated !== false)
			) ??
			$settings?.tools ??
			[];
		selectedSkillIds = (meta?.skillIds ?? []).filter((skillId: string) =>
			($skills as any[]).some((skill) => skill.id === skillId && skill.is_active)
		);
		selectedFilterIds = (meta?.defaultFilterIds ?? []).filter((filterId: string) =>
			selectedModel.filters?.some((filter: { id: string }) => filter.id === filterId)
		);
		webSearchEnabled = defaultFeature('web_search');
		imageGenerationEnabled = defaultFeature('image_generation');
		codeInterpreterEnabled = defaultFeature('code_interpreter');
	};
	$: if (!id && sideModelId) void applyModelDefaults(sideModelId);
	$: toolApprovalMode = resolveToolApprovalMode(
		params?.tool_approval_mode ?? $settings?.params?.tool_approval_mode,
		$config?.features?.enable_tool_permissions_auto ?? false
	);
	let interactions: { id: string; type: string; data: any; callback: (value: any) => void }[] = [];
	$: interaction = interactions[0];
	const resolveInteraction = (pending: typeof interaction, value: any) => {
		if (!interactions.includes(pending)) return;
		interactions = interactions.filter((item) => item !== pending);
		pending.callback(value);
	};
	const cancelInteractions = () => {
		for (const pending of interactions)
			resolveInteraction(pending, { status: 'cancelled', answers: {} });
	};
	$: askUser = {
		id: interaction?.id,
		show: interaction?.type === 'request:user_input',
		questions: interaction?.data?.questions ?? [],
		allowOther: interaction?.data?.allow_other ?? true,
		timeoutMs: interaction?.data?.timeout_ms ?? null,
		onConfirm: (value: any) => resolveInteraction(interaction, value),
		onCancel: () => resolveInteraction(interaction, { status: 'cancelled', answers: {} })
	};
	const resolvePendingAskUser = async (action: 'answer' | 'reject', answers?: unknown) => {
		const { message, call } = pendingAskUser;
		error = '';
		try {
			await resolveChatMessageToolCall(
				localStorage.token,
				id,
				message.id,
				call.call_id || call.id,
				action,
				{ answers }
			);
			// reconnect reads done to tell whether the resumed reply is still running
			message.done = false;
		} catch (err) {
			error = getErrorMessage(err);
		}
		void reconnect();
	};
	$: pendingAskUser =
		[...messages]
			.reverse()
			.filter((message) => (message.user_id ? message.user_id === $user?.id : !isShared))
			.map(getPendingAskUserFromMessage)
			.find(Boolean) ?? null;
	$: savedAskUserPrompt = pendingAskUser
		? {
				show: true,
				questions: Array.isArray(pendingAskUser.args?.questions)
					? pendingAskUser.args.questions
					: [],
				allowOther: pendingAskUser.args?.allow_other !== false,
				timeoutMs: null,
				onConfirm: (value: any) => void resolvePendingAskUser('answer', value?.answers ?? {}),
				onCancel: () => void resolvePendingAskUser('reject')
			}
		: null;
	let system = [
		systemPrompt,
		'This is a separate side conversation. Earlier messages are reference context only. Answer the side question; do not continue the parent task.'
	]
		.filter(Boolean)
		.join('\n\n');
	let id = chatId;
	let messages: any[] = [];
	let draft = initialView?.draft ?? '';
	let error = '';
	let busy = false;
	let sending = false;
	let recovering = false;
	let receivedDuringRecovery = new Set<string>();
	let disposed = false;
	let request: Promise<any> | null = null;
	let scroller: HTMLDivElement;
	let autoScroll = true;
	let input: MessageInput;
	const inputId = `side-chat-input-${uuidv4()}`;
	const messagesContainerId = `${inputId}-messages`;
	$: sideHistory = {
		currentId: messages.at(-1)?.id ?? null,
		messages: Object.fromEntries(
			messages.map((message, index) => [
				message.id,
				// The copied context belongs to saved history, outside this panel's visible branch.
				index === 0 ? { ...message, parentId: null } : message
			])
		)
	};
	const scroll = async () => {
		await tick();
		if (autoScroll) scroller?.scrollTo({ top: scroller.scrollHeight });
	};

	const receive = (event: any, callback?: (value: any) => void) => {
		if (!id || event.chat_id !== id) return;
		const { type, data } = event.data ?? {};
		if (recovering && event.message_id) receivedDuringRecovery.add(event.message_id);
		if (type === 'chat:title') {
			onChatUpdate({ id, title: data });
			void refreshChatList(localStorage.token);
			return;
		}
		if (type === 'chat:tags') {
			void getAllTags(localStorage.token).then((value) => tags.set(value));
			return;
		}
		if (type === 'context_compaction') {
			const checkpoint = [...context, ...messages].find(
				(message) => message.id === data.checkpoint_message_id
			);
			if (checkpoint && data.context_summary) checkpoint.contextSummary = data.context_summary;
			return;
		}
		if (type === 'request:interaction:done') {
			interactions = interactions.filter((item) => item.id !== data.interaction_id);
			return;
		}
		if (
			callback &&
			['request:user_input', 'request:elicitation', 'confirmation', 'input'].includes(type)
		) {
			if (!canSend) callback({ status: 'cancelled', answers: {} });
			else if (data?.tool_call && toolApprovalMode === 'full') callback(true);
			else
				interactions = [
					...interactions,
					{ id: data.interaction_id ?? uuidv4(), type, data, callback }
				];
			return;
		}
		const message = messages.find((m) => m.id === event.message_id);
		if (!message) return;
		if (type === 'response:completion')
			message.output = applyResponseStreamEvent(message.output, data);
		else if (type === 'chat:completion') {
			if (data.output) message.output = data.output;
			else if (data.content !== undefined) message.content = data.content;
			if (data.done) {
				message.done = true;
				busy = false;
				if (!temporary)
					$socket?.emit('events:chat', { chat_id: id, data: { type: 'last_read_at' } });
			}
		} else if (type === 'chat:message:error') {
			error = getErrorMessage(data.error);
			message.done = true;
			busy = false;
		} else if (type === 'status') {
			message.statusHistory = [...(message.statusHistory ?? []), data];
		} else if (type === 'source' || type === 'citation') {
			message.sources = [...(message.sources ?? []), data];
		} else if (type === 'chat:message:files' || type === 'files') {
			message.files = [...(message.files ?? []), ...data.files];
		} else if (type === 'chat:message' || type === 'replace') {
			message.content = data.content;
		} else if (type === 'chat:message:delta' || type === 'message') {
			message.content += data.content;
		} else if (type === 'chat:tasks:cancel') {
			cancelInteractions();
			if (data.output) message.output = data.output;
			message.done = true;
			busy = false;
		}
		messages = messages;
		void scroll();
	};

	const reconnect = async () => {
		if (!sideChatAllowed || (!temporary && !canSave) || !id || !$socket?.id || recovering) return;
		recovering = true;
		receivedDuringRecovery = new Set();
		try {
			if (!temporary) {
				const tasks = await getTaskIdsByChatId(localStorage.token, id);
				const saved = await getChatById(localStorage.token, id);
				if (disposed || !sideChatAllowed) return;
				isShared = saved.user_id !== $user?.id;
				readOnly = isShared && saved.chat.share_mode !== 'continue';
				if (!loaded) {
					selectedModels = [saved.chat.models?.[0] ?? modelId];
					params = { ...saved.chat.params };
					system = params.system ?? saved.chat.system ?? $settings.system ?? '';
				}
				const savedHistory = saved.chat.history ?? convertMessagesToHistory(saved.chat.messages);
				messages = createMessagesList(
					savedHistory,
					saved.current_message_id ?? savedHistory.currentId
				)
					.filter((message) => !contextIds.has(message.id))
					.map((message) =>
						receivedDuringRecovery.has(message.id)
							? (messages.find((local) => local.id === message.id) ?? message)
							: message
					);
				busy = !!tasks.task_ids.length && messages.at(-1)?.done === false;
				if (!busy) messages = messages.map((message) => ({ ...message, done: true }));
				loaded = true;
				onChatUpdate({ id, title: saved.title });
				void scroll();
				return;
			}
			const result = await resumeTemporaryChat(localStorage.token, id, $socket.id);
			if (disposed || !canSend) return;
			for (const stream of result.streams) {
				const message = messages.find((m) => m.id === stream.message_id);
				if (message && !message.done) message.output = stream.output;
			}

			if (busy && !result.task_ids.length) {
				busy = false;
				error = $i18n.t('Connection lost. Please retry.');
				messages.forEach((m) => {
					m.done = true;
				});
			}
			messages = messages;
		} catch (err) {
			error = getErrorMessage(err);
			busy = false;
			messages = messages.map((message) => ({ ...message, done: true }));
		} finally {
			recovering = false;
		}
	};

	const send = async () => {
		if (!canSend || disposed) return;
		const question = draft.trim();
		if ((!question && !files.length) || busy || sending || recovering || pendingAskUser) return;
		if (!atSelectedModel && selectedModels.length !== 1) {
			error = $i18n.t('Select only one model');
			return;
		}
		if (files.some((file) => file.status === 'uploading' || file.status === 'error')) {
			error = $i18n.t('Please wait for files to finish uploading.');
			return;
		}
		if (!$socket?.connected || !sideModelId) {
			error = $i18n.t('Connect and select a model first.');
			return;
		}
		error = '';
		sending = true;
		try {
			if (!id) {
				if (temporary) id = createTemporaryChatId($socket.id);
				else {
					const created = await createNewChat(
						localStorage.token,
						{
							title: question.slice(0, 100) || $i18n.t('New Chat'),
							...(originalChatId && {
								originalChatId,
								branchPointMessageId: context.at(-1)?.id ?? null
							}),
							models: [sideModelId],
							params: { ...params, system },
							history: convertMessagesToHistory(context),
							messages: context,
							files: context.flatMap((message) => message.files ?? []),
							tags: [],
							timestamp: Date.now()
						},
						parentFolderId
					);
					if (!created?.id) throw new Error($i18n.t('Failed to create chat'));
					id = created.id;
					onChatUpdate({ id, title: created.title });
					void refreshChatList(localStorage.token);
					if (created.folder_id) void refreshFolderChatLists(created.folder_id, created);
				}
				if (disposed) return;
				openSideChatIds.update((ids) => new Set([...ids, id]));
			} else if (!temporary && !isShared) {
				await updateChatById(localStorage.token, id, { params: { ...params, system } });
			}
			await tick();
			if (!canSend || disposed) return;
			if (!(await input?.uploadPendingFiles(id)) || busy || !canSend || disposed) return;
			const userMessage = {
				id: uuidv4(),
				parentId: messages.at(-1)?.id ?? (temporary ? null : (context.at(-1)?.id ?? null)),
				childrenIds: [] as string[],
				role: 'user',
				content: question,
				files: [...files],
				done: true,
				timestamp: Math.floor(Date.now() / 1000),
				models: [sideModelId]
			};
			const answer = {
				id: uuidv4(),
				parentId: userMessage.id,
				childrenIds: [] as string[],
				role: 'assistant',
				user_id: $user?.id,
				content: '',
				output: [],
				done: false,
				timestamp: Math.floor(Date.now() / 1000),
				model: sideModelId
			};
			userMessage.childrenIds.push(answer.id);
			if (messages.length) messages.at(-1).childrenIds.push(userMessage.id);
			const conversation = [...context, ...messages, userMessage].map((message) => {
				if (message.role === 'assistant' && message.output?.length)
					return {
						id: message.id,
						role: message.role,
						output: message.output,
						contextSummary: message.contextSummary
					};
				const images = (message.files ?? []).filter(
					(file: any) => file.type === 'image' || isRasterImageContentType(file.content_type)
				);
				return {
					id: message.id,
					role: message.role,
					contextSummary: message.contextSummary,
					content: images.length
						? [
								{ type: 'text', text: message.content ?? '' },
								...images.map((file: any) => ({ type: 'image_url', image_url: { url: file.url } }))
							]
						: message.content
				};
			});
			const requestFiles = [...context, ...messages, userMessage].flatMap(
				(message) => message.files ?? []
			);
			const directServers = selectedToolIds
				.filter((id) => id.startsWith('direct_server:'))
				.map((id) => id.slice('direct_server:'.length));
			messages = [...messages, userMessage, answer];
			draft = '';
			files = [];
			autoScroll = true;
			input?.setText('');
			busy = true;
			void scroll();
			request = generateOpenAIChatCompletion(localStorage.token, {
				model: sideModelId,
				model_item: $models.find((model) => model.id === sideModelId),
				stream: true,
				chat_id: id,
				session_id: $socket.id,
				id: answer.id,
				user_message: userMessage,
				...(!temporary &&
					!isShared && {
						parent_id: userMessage.parentId,
						background_tasks:
							messages.length === 2
								? {
										title_generation: $settings?.title?.auto ?? true,
										tags_generation: $settings?.autoTags ?? true
									}
								: {}
					}),
				params: { ...params, tool_approval_mode: toolApprovalMode },
				files: requestFiles,
				tool_ids: selectedToolIds.filter((id) => !id.startsWith('direct_server:')),
				skill_ids: selectedSkillIds,
				filter_ids: selectedFilterIds,
				terminal_id: $config?.features?.enable_tool_servers ? $selectedTerminalId : undefined,
				tool_servers: $config?.features?.enable_tool_servers
					? [
							...($toolServers ?? []).filter(
								(server: any, index) =>
									directServers.includes(String(index)) || directServers.includes(server.id)
							),
							...($terminalServers ?? []).filter((server) => !server.id)
						]
					: [],
				features: {
					web_search: webSearchEnabled,
					image_generation: imageGenerationEnabled,
					code_interpreter: codeInterpreterEnabled,
					memory: $settings.memory ?? $config?.features?.enable_memories ?? false
				},
				messages: [{ role: 'system', content: system }, ...(temporary ? conversation : [])]
			});
			const result = await request;
			if (result?.error) throw result.error;
		} catch (err) {
			error = getErrorMessage(err);
			if (busy && messages.at(-1)) messages.at(-1).done = true;
			busy = false;
			messages = messages;
		} finally {
			request = null;
			sending = false;
		}
	};

	const stop = async () => {
		cancelInteractions();
		await request?.catch(() => {});
		if (!id) return;
		try {
			await stopTasksByChatId(localStorage.token, id);
			busy = false;
			messages.forEach((m) => {
				m.done = true;
			});
			messages = messages;
		} catch (err) {
			if (!disposed) error = getErrorMessage(err);
		}
	};

	$: if (!canSend) {
		cancelInteractions();
		if (busy && !readOnly) void stop();
	}

	onMount(() => {
		const connection = $socket;
		connection?.on('events', receive);
		connection?.on('connect', reconnect);
		connection?.on('disconnect', cancelInteractions);
		if (id) {
			openSideChatIds.update((ids) => new Set([...ids, id]));
			void reconnect();
		}
		void tick().then(() => {
			if (disposed) return;
			if (initialView) input?.setText(draft);
			if (canSend && initialPrompt && !initialView) {
				draft = initialView?.draft ?? initialPrompt;
				input?.setText(draft);
				void send();
			}
			input?.focus();
		});
		return () => {
			disposed = true;
			connection?.off('events', receive);
			connection?.off('connect', reconnect);
			connection?.off('disconnect', cancelInteractions);
			cancelInteractions();
			if (id) {
				if (temporary) void stop();
				openSideChatIds.update((ids) => {
					const next = new Set(ids);
					next.delete(id);
					return next;
				});
			}
		};
	});
</script>

<div
	id={`${inputId}-pane`}
	class="relative flex h-full min-h-0 min-w-0 w-full flex-col @container overflow-hidden"
>
	<FilesOverlay show={dragged} />
	<div
		id={messagesContainerId}
		bind:this={scroller}
		class="flex-1 min-h-0 overflow-y-auto pb-2.5 scrollbar-hidden"
		on:scroll={() => {
			autoScroll = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 50;
		}}
	>
		{#if messages.length}
			<Messages
				className="flex pt-4"
				chatId={id}
				history={sideHistory}
				selectedModels={[sideModelId]}
				prompt={draft}
				atSelectedModel={undefined}
				readOnly
				forkHandler={null}
				shareMode={null}
				sendMessage={() => {}}
				continueResponse={() => {}}
				regenerateResponse={() => {}}
				mergeResponses={() => {}}
				chatActionHandler={() => {}}
				allowDelete={false}
				allowToolApproval={canSend}
				onToolCallResolved={(res: { message_id: string }) => {
					// reconnect reads done to tell whether the resumed reply is still running
					const message = messages.find((m) => m.id === res.message_id);
					if (message) message.done = false;
					void reconnect();
				}}
				editCodeBlock={false}
				{autoScroll}
				{messagesContainerId}
			/>
		{:else if loaded}
			<div class="flex h-full items-center justify-center px-6">
				<div class="max-w-56 text-center">
					<p class="text-sm font-normal text-gray-600 dark:text-gray-300">
						{temporary ? $i18n.t('Temporary chat') : $i18n.t('New Chat')}
					</p>
					<p class="mt-1.5 text-xs leading-relaxed text-gray-400 dark:text-gray-500">
						{temporary
							? $i18n.t('Messages disappear when you close this tab.')
							: $i18n.t('Messages are saved to your chats.')}
					</p>
				</div>
			</div>
		{/if}
	</div>
	<div class="shrink-0 pb-2 z-10">
		{#if error}<p role="alert" class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
				{error}
			</p>{/if}
		{#if canSend}
			<MessageInput
				bind:this={input}
				bind:dragged
				bind:prompt={draft}
				bind:autoScroll
				chatId={id}
				history={sideHistory}
				bind:selectedModels
				multipleModels={false}
				bind:atSelectedModel
				bind:files
				bind:params
				bind:selectedToolIds
				bind:selectedSkillIds
				bind:selectedFilterIds
				bind:webSearchEnabled
				bind:imageGenerationEnabled
				bind:codeInterpreterEnabled
				{toolApprovalMode}
				onToolApprovalModeChange={(mode: string) => {
					params = { ...params, tool_approval_mode: mode };
				}}
				askUser={savedAskUserPrompt ?? askUser}
				dropzoneId={`${inputId}-pane`}
				{inputId}
				{messagesContainerId}
				{temporary}
				onTemporaryChange={(value) => {
					if (!id && !sending) temporary = value;
				}}
				embedded
				callEnabled={false}
				terminalSelectionEnabled={false}
				generating={busy}
				stopResponse={stop}
				createMessagePair={() => {}}
				on:submit={() => void send()}
			/>
		{:else if loaded}
			<p role="status" class="px-4 py-2 text-xs text-gray-500">
				{$i18n.t('You do not have permission to use side chat.')}
			</p>
		{/if}
	</div>
</div>

{#if interaction}
	{#key interaction.id}
		{@const pending = interaction}
		{#if pending.type === 'request:elicitation'}
			<ElicitationDialog
				data={pending.data}
				onResponse={(value) => resolveInteraction(pending, value)}
			/>
		{:else if pending.type === 'confirmation' || pending.type === 'input'}
			<ConfirmDialog
				show={true}
				title={pending.data.title ?? $i18n.t('Tool Permissions')}
				message={pending.data.message ?? ''}
				input={pending.type === 'input'}
				inputPlaceholder={pending.data.placeholder ?? ''}
				inputValue={pending.data.value ?? ''}
				inputType={pending.data.input?.type ?? ''}
				inputOptions={pending.data.input?.options ?? []}
				on:confirm={(event) =>
					resolveInteraction(pending, pending.type === 'input' ? event.detail : true)}
				on:cancel={() => resolveInteraction(pending, false)}
			>
				{#if pending.data.tool_call}
					<div class="text-sm text-gray-500">
						<div class="font-medium break-all">{pending.data.tool_call.name}</div>
						<pre class="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(
								pending.data.tool_call.arguments,
								null,
								2
							)}</pre>
					</div>
				{/if}
			</ConfirmDialog>
		{/if}
	{/key}
{/if}
