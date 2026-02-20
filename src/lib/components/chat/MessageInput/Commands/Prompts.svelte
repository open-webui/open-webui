<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { tick, getContext, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let prompts = [];
	export let onSelect = (e) => {};

	let selectedPromptIdx = 0;
	export let filteredItems = [];
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let debouncedQuery = '';

	// OpenClaw slash commands — these are surfaced in the / picker so users
	// get autocomplete and descriptions without needing to memorize them.
	// Commands that take arguments have a trailing space in `content` so the
	// cursor lands after the command ready for the argument.
	const OPENCLAW_COMMANDS = [
		// Session
		{ command: 'new', name: 'Start a new session', content: '/new'},
		{ command: 'reset', name: 'Reset the current session', content: '/reset'},
		{ command: 'compact', name: 'Compact the session context', content: '/compact '},
		{ command: 'stop', name: 'Stop the current run', content: '/stop'},
		// Options
		{ command: 'model', name: 'Show or set the model', content: '/model '},
		{ command: 'models', name: 'List model providers or provider models', content: '/models'},
		{ command: 'think', name: 'Set thinking level (auto/low/medium/high)', content: '/think '},
		{ command: 'verbose', name: 'Toggle verbose mode (on/off)', content: '/verbose '},
		{ command: 'reasoning', name: 'Toggle reasoning visibility', content: '/reasoning'},
		{ command: 'elevated', name: 'Toggle elevated mode', content: '/elevated'},
		{ command: 'queue', name: 'Adjust queue settings', content: '/queue '},
		// Status
		{ command: 'help', name: 'Show available commands', content: '/help'},
		{ command: 'commands', name: 'List all slash commands', content: '/commands'},
		{ command: 'status', name: 'Show current agent status', content: '/status'},
		{ command: 'whoami', name: 'Show your sender ID', content: '/whoami'},
		{ command: 'context', name: 'Explain how context is built and used', content: '/context'},
		{ command: 'usage', name: 'Show usage or cost summary', content: '/usage'},
		// Management
		{ command: 'allowlist', name: 'List / add / remove allowlist entries', content: '/allowlist '},
		{ command: 'approve', name: 'Approve or deny exec requests', content: '/approve '},
		{ command: 'subagents', name: 'List / stop / log subagent runs', content: '/subagents'},
		{ command: 'activation', name: 'Set group activation mode', content: '/activation '},
		{ command: 'send', name: 'Set send policy', content: '/send '},
		{ command: 'exec', name: 'Set exec defaults for this session', content: '/exec '},
		// Tools
		{ command: 'skill', name: 'Run a skill by name', content: '/skill '},
		{ command: 'restart', name: 'Restart OpenClaw', content: '/restart'},
		{ command: 'weather', name: 'Get current weather and forecasts', content: '/weather '},
		{ command: 'github', name: 'Interact with GitHub via gh CLI', content: '/github '},
		{ command: 'tmux', name: 'Remote-control tmux sessions', content: '/tmux '},
		{ command: 'browser_extract', name: 'Extract structured data from web pages', content: '/browser_extract '},
		{ command: 'video_frames', name: 'Extract frames or clips from videos', content: '/video_frames '},
		{ command: 'openai_whisper', name: 'Local speech-to-text (Whisper)', content: '/openai_whisper '},
		// Media
		{ command: 'tts', name: 'Control text-to-speech (TTS)', content: '/tts '},
		// Plugins
		{ command: 'otto', name: 'Otto CRM direct commands', content: '/otto '},
	].map((cmd) => ({ ...cmd, _openclaw: true }));

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			debouncedQuery = query;
		}, 200);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: filteredOpenClaw = OPENCLAW_COMMANDS.filter(
		(c) =>
			c.command.toLowerCase().includes(debouncedQuery.toLowerCase()) ||
			c.name.toLowerCase().includes(debouncedQuery.toLowerCase())
	);

	$: filteredPrompts = prompts
		.filter((p) => p.command.toLowerCase().includes(debouncedQuery.toLowerCase()))
		.sort((a, b) => a.name.localeCompare(b.name))
		.map((p) => ({ ...p, _openclaw: false }));

	$: filteredItems = [...filteredOpenClaw, ...filteredPrompts];

	$: if (query) {
		selectedPromptIdx = 0;
	}

	export const selectUp = () => {
		selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
	};
	export const selectDown = () => {
		selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const command = filteredItems[selectedPromptIdx];
		if (command) {
			onSelect({ type: 'prompt', data: command });
		}
	};
</script>

{#if filteredOpenClaw.length > 0}
	<div class="px-2 text-xs text-gray-400 dark:text-gray-500 py-1 font-medium tracking-wide uppercase">
		Commands
	</div>
	<div class="space-y-0.5 scrollbar-hidden">
		{#each filteredOpenClaw as item, idx}
			{@const globalIdx = idx}
			<button
				class="px-3 py-1.5 rounded-xl w-full text-left flex items-baseline gap-2 {globalIdx === selectedPromptIdx
					? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
					: 'hover:bg-gray-50 dark:hover:bg-gray-800'}"
				type="button"
				on:click={() => {
					onSelect({ type: 'prompt', data: item });
				}}
				on:mousemove={() => {
					selectedPromptIdx = globalIdx;
				}}
				on:focus={() => {}}
				data-selected={globalIdx === selectedPromptIdx}
			>
				<span class="font-mono font-semibold text-sm text-blue-600 dark:text-blue-400 shrink-0">
					/{item.command}
				</span>
				<span class="text-xs text-gray-500 dark:text-gray-400 truncate">
					{item.name}
				</span>
			</button>
		{/each}
	</div>
{/if}

{#if filteredPrompts.length > 0}
	<div class="px-2 text-xs text-gray-400 dark:text-gray-500 py-1 font-medium tracking-wide uppercase {filteredOpenClaw.length > 0 ? 'mt-1 border-t border-gray-100 dark:border-gray-800 pt-2' : ''}">
		{$i18n.t('Prompts')}
	</div>
	<div class="space-y-0.5 scrollbar-hidden">
		{#each filteredPrompts as promptItem, idx}
			{@const globalIdx = filteredOpenClaw.length + idx}
			<Tooltip content={promptItem.name} placement="top-start">
				<button
					class="px-3 py-1 rounded-xl w-full text-left {globalIdx === selectedPromptIdx
						? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
						: 'hover:bg-gray-50 dark:hover:bg-gray-800'} truncate"
					type="button"
					on:click={() => {
						onSelect({ type: 'prompt', data: promptItem });
					}}
					on:mousemove={() => {
						selectedPromptIdx = globalIdx;
					}}
					on:focus={() => {}}
					data-selected={globalIdx === selectedPromptIdx}
				>
					<span class="font-medium text-black dark:text-gray-100">
						{promptItem.command}
					</span>
					<span class="text-xs text-gray-600 dark:text-gray-100">
						{promptItem.name}
					</span>
				</button>
			</Tooltip>
		{/each}
	</div>
{/if}
