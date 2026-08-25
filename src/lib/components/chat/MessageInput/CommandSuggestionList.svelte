<script lang="ts">
	import SlashCommands from './Commands/SlashCommands.svelte';
	import AtCommands from './Commands/AtCommands.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Skills from './Commands/Skills.svelte';
	import Emojis from './Commands/Emojis.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';

	export let char = '';
	export let query = '';
	export let command: (payload: {
		id: string;
		label: string;
		content?: string;
		type?: string;
	}) => void;

	export let onSelect: (e: any) => void = () => {};
	export let onUpload: (e: any) => void = () => {};
	export let onCompact: () => void = () => {};
	export let onStatus: () => void = () => {};
	export let onFork: () => void = () => {};
	export let onModel: () => void = () => {};
	export let onSettings: () => void = () => {};
	export let onTemporary: () => void = () => {};
	export let insertTextHandler: (text: string) => void = () => {};
	export let canCompact: boolean | (() => boolean) = false;
	export let compactDisabled: boolean | (() => boolean) = false;
	export let canStatus: boolean | (() => boolean) = false;
	export let canFork: boolean | (() => boolean) = false;
	export let forkDisabled: boolean | (() => boolean) = false;
	export let canTemporary: boolean | (() => boolean) = false;
	export let temporaryEnabled: boolean | (() => boolean) = false;
	export let contextUsage = null;

	$: compactAvailable = typeof canCompact === 'function' ? canCompact() : canCompact;
	$: isCompactDisabled =
		typeof compactDisabled === 'function' ? compactDisabled() : compactDisabled;
	$: statusAvailable = typeof canStatus === 'function' ? canStatus() : canStatus;
	$: forkAvailable = typeof canFork === 'function' ? canFork() : canFork;
	$: isForkDisabled = typeof forkDisabled === 'function' ? forkDisabled() : forkDisabled;
	$: temporaryAvailable = typeof canTemporary === 'function' ? canTemporary() : canTemporary;
	$: isTemporaryEnabled =
		typeof temporaryEnabled === 'function' ? temporaryEnabled() : temporaryEnabled;
	$: resolvedContextUsage = typeof contextUsage === 'function' ? contextUsage() : contextUsage;
	$: contextHasThreshold = Number(resolvedContextUsage?.threshold) > 0;
	$: contextPercent = contextHasThreshold
		? Math.max(0, Math.round(resolvedContextUsage?.percent ?? 0))
		: null;

	let suggestionElement: any = null;
	let filteredItems: any[] = [];

	const onKeyDown = (event: KeyboardEvent) => {
		if (!['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(event.key)) return false;

		if (event.key === 'ArrowUp') {
			suggestionElement?.selectUp();
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'ArrowDown') {
			suggestionElement?.selectDown();
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'Enter' || event.key === 'Tab') {
			suggestionElement?.select();

			if (event.key === 'Enter') {
				event.preventDefault();
			}
			return true;
		}
		if (event.key === 'Escape') {
			return true;
		}
		return false;
	};

	// This method will be called from the suggestion renderer
	// @ts-ignore
	export function _onKeyDown(event: KeyboardEvent) {
		return onKeyDown(event);
	}
</script>

<div class={(filteredItems ?? []).length > 0 ? '' : 'hidden'} id="suggestions-container">
	<DropdownMenu className="w-72 max-w-[calc(100vw-1rem)] overflow-x-hidden font-sans text-xs">
		<div class="max-h-60 overflow-y-auto overflow-x-hidden scrollbar-thin">
			{#if char === '/'}
				<SlashCommands
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					canCompact={compactAvailable}
					compactDisabled={isCompactDisabled}
					canStatus={statusAvailable}
					canFork={forkAvailable}
					forkDisabled={isForkDisabled}
					canTemporary={temporaryAvailable}
					temporaryEnabled={isTemporaryEnabled}
					{contextPercent}
					{contextHasThreshold}
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'prompt') {
							command({
								id: data.command,
								label: data.command,
								content: data.content,
								type: 'prompt'
							});
						} else if (type === 'command' && data.id === 'compact') {
							command({ id: data.id, label: data.id });
							onCompact();
						} else if (type === 'command' && data.id === 'status') {
							command({ id: data.id, label: data.id });
							onStatus();
						} else if (type === 'command' && data.id === 'fork') {
							command({ id: data.id, label: data.id });
							onFork();
						} else if (type === 'command' && data.id === 'model') {
							command({ id: data.id, label: data.id });
							onModel();
						} else if (type === 'command' && data.id === 'settings') {
							command({ id: data.id, label: data.id });
							onSettings();
						} else if (type === 'command' && data.id === 'temporary') {
							command({ id: data.id, label: data.id });
							onTemporary();
						} else if (type === 'skill') {
							command({
								id: `${data.id}|${data.name}`,
								label: data.name
							});

							onSelect({
								type: 'skill',
								data: data
							});
						}
					}}
				/>
			{:else if char === '#'}
				<Knowledge
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'knowledge') {
							insertTextHandler('');

							onUpload({
								type: 'file',
								data: data
							});
						} else if (type === 'web') {
							insertTextHandler('');

							onUpload({
								type: 'web',
								data: data
							});
						}
					}}
				/>
			{:else if char === '@'}
				<AtCommands
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'model') {
							insertTextHandler('');

							onSelect({
								type: 'model',
								data: data
							});
						} else if (type === 'knowledge') {
							insertTextHandler('');

							onUpload({
								type: 'file',
								data: data
							});
						} else if (type === 'filesystem') {
							insertTextHandler('');

							onUpload({
								type: 'filesystem',
								data: data
							});
						} else if (type === 'web') {
							insertTextHandler('');

							onUpload({
								type: 'web',
								data: data
							});
						}
					}}
				/>
			{:else if char === '$'}
				<Skills
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'skill') {
							command({
								id: `${data.id}|${data.name}`,
								label: data.name
							});

							onSelect({
								type: 'skill',
								data: data
							});
						}
					}}
				/>
			{:else if char === ':'}
				<Emojis
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'emoji') {
							command({
								id: data.name,
								label: data.shortCodes[0]
							});
						}
					}}
				/>
			{/if}
		</div>
	</DropdownMenu>
</div>
