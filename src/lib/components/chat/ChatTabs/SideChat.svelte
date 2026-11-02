<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import {
		socket,
		user,
		openTemporaryChatIds,
		sideChatRequest,
		models,
		settings,
		config,
		toolServers,
		terminalServers,
		selectedTerminalId,
		type Model
	} from '$lib/stores';
	import { createTemporaryChatId } from '$lib/utils/chatId';
	import { generateOpenAIChatCompletion, getErrorMessage } from '$lib/apis/openai';
	import { resumeTemporaryChat, stopTasksByChatId } from '$lib/apis';
	import { applyResponseStreamEvent } from '../Messages/structuredOutput';
	import Messages from '../Messages.svelte';
	import MessageInput from '../MessageInput.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ElicitationDialog from '../ElicitationDialog.svelte';
	import { isRasterImageContentType } from '$lib/utils';

	export let parentId: string;
	export let history;
	export let modelId: string;
	export let systemPrompt = '';
	const i18n = getContext<any>('i18n');
	$: sideChatAllowed =
		$user?.role === 'admin' ||
		($user?.role === 'user' &&
			($user.permissions?.chat?.temporary ?? true) &&
			($user.permissions?.chat?.side_chat ?? false));
	// Snapshot the active branch once; later parent edits and streaming stay in the parent.
	const context = (() => {
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
			branch.map(({ id, role, content, output, files, contextSummary }) => ({
				id,
				role,
				files,
				contextSummary,
				...(output?.length && role === 'assistant' ? { output } : { content: content ?? '' })
			}))
		);
	})();
	let selectedModels = [modelId];
	let atSelectedModel: Model | undefined = undefined;
	$: sideModelId = atSelectedModel?.id ?? selectedModels[0];
	let files: any[] = [];
	let params: Record<string, any> = { ...$settings.params };
	let selectedToolIds: string[] = [];
	let selectedSkillIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let webSearchEnabled = false;
	let imageGenerationEnabled = false;
	let codeInterpreterEnabled = false;
	$: toolApprovalMode =
		(params.tool_approval_mode ?? $settings.params?.tool_approval_mode) === 'ask' ? 'ask' : 'full';
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
	const system = systemPrompt;
	let id = '';
	let messages: any[] = [];
	let draft = '';
	let error = '';
	let busy = false;
	let ready = false;
	let disposed = false;
	let request: Promise<any> | null = null;
	let scroller: HTMLDivElement;
	let autoScroll = true;
	let input: MessageInput;
	const inputId = `side-chat-input-${uuidv4()}`;
	const messagesContainerId = `${inputId}-messages`;
	$: sideHistory = {
		currentId: messages.at(-1)?.id ?? null,
		messages: Object.fromEntries(messages.map((message) => [message.id, message]))
	};
	const scroll = async () => {
		await tick();
		if (autoScroll) scroller?.scrollTo({ top: scroller.scrollHeight });
	};

	const receive = (event: any, callback?: (value: any) => void) => {
		if (!id || event.chat_id !== id) return;
		const { type, data } = event.data ?? {};
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
			if (!sideChatAllowed) callback({ status: 'cancelled', answers: {} });
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
		if (!sideChatAllowed || !id || !$socket?.id) return;
		try {
			const result = await resumeTemporaryChat(localStorage.token, id, $socket.id);
			if (disposed || !sideChatAllowed) return;
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
		}
	};

	const send = async () => {
		if (!sideChatAllowed) return;
		const question = draft.trim();
		if ((!question && !files.length) || busy) return;
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
		if (!id) {
			id = createTemporaryChatId($socket.id);
			openTemporaryChatIds.update((ids) => new Set([...ids, id]));
		}
		await tick();
		if (!sideChatAllowed) return;
		if (!(await input?.uploadPendingFiles(id)) || busy || !sideChatAllowed) return;
		const userMessage = {
			id: uuidv4(),
			parentId: messages.at(-1)?.id ?? null,
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
			messages: [
				...(system ? [{ role: 'system', content: system }] : []),
				{
					role: 'system',
					content:
						'This is a separate side conversation. Earlier messages are reference context only. Answer the side question; do not continue the parent task.'
				},
				...conversation
			]
		});
		try {
			const result = await request;
			if (result?.error) throw result.error;
		} catch (err) {
			error = getErrorMessage(err);
			answer.done = true;
			busy = false;
			messages = messages;
		} finally {
			request = null;
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

	$: if (!sideChatAllowed) {
		cancelInteractions();
		if (busy) void stop();
	}

	$: if (ready && $sideChatRequest?.parentId === parentId) {
		const pending = $sideChatRequest;
		sideChatRequest.set(null);
		if (sideChatAllowed && pending.prompt) {
			draft = pending.prompt;
			input?.setText(draft);
			if (!busy) void send();
		}
		input?.focus();
	}
	onMount(() => {
		const connection = $socket;
		connection?.on('events', receive);
		connection?.on('connect', reconnect);
		connection?.on('disconnect', cancelInteractions);
		ready = true;
		input?.focus();
		return () => {
			disposed = true;
			connection?.off('events', receive);
			connection?.off('connect', reconnect);
			connection?.off('disconnect', cancelInteractions);
			cancelInteractions();
			if (id) {
				void stop();
				openTemporaryChatIds.update((ids) => {
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
	class="flex h-full min-h-0 min-w-0 w-full flex-col @container overflow-hidden"
>
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
				editCodeBlock={false}
				{autoScroll}
				{messagesContainerId}
			/>
		{:else}
			<div class="flex h-full items-center justify-center px-6">
				<div class="max-w-56 text-center">
					<p class="text-sm font-normal text-gray-600 dark:text-gray-300">
						{$i18n.t('Temporary chat')}
					</p>
					<p class="mt-1.5 text-xs leading-relaxed text-gray-400 dark:text-gray-500">
						{$i18n.t('Messages disappear when you close this tab.')}
					</p>
				</div>
			</div>
		{/if}
	</div>
	<div class="shrink-0 pb-2 z-10">
		{#if error}<p role="alert" class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{error}</p>{/if}
		{#if sideChatAllowed}
			<MessageInput
				bind:this={input}
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
				{askUser}
				dropzoneId={`${inputId}-pane`}
				{inputId}
				{messagesContainerId}
				temporary={true}
				embedded
				callEnabled={false}
				terminalSelectionEnabled={false}
				generating={busy}
				stopResponse={stop}
				createMessagePair={() => {}}
				on:submit={() => void send()}
			/>
		{:else}
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
