<script lang="ts">
	import { prompts } from '$lib/stores';
	import { findWordIndices } from '$lib/utils';
	import { tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let files;
	export let prompt = '';
	let selectedCommandIdx = 0;
	let filteredPromptCommands = [];

	$: filteredPromptCommands = $prompts
		.filter((p) => p.command.includes(prompt))
		.sort((a, b) => a.title.localeCompare(b.title));

	$: if (prompt) {
		selectedCommandIdx = 0;
	}

	export const selectUp = () => {
		selectedCommandIdx = Math.max(0, selectedCommandIdx - 1);
	};

	export const selectDown = () => {
		selectedCommandIdx = Math.min(selectedCommandIdx + 1, filteredPromptCommands.length - 1);
	};

	const confirmCommand = async (command) => {
		let text = command.content;

		if (command.content.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			console.log(clipboardText);

			const clipboardItems = await navigator.clipboard.read();

			let imageUrl = null;
			for (const item of clipboardItems) {
				// Check for known image types
				for (const type of item.types) {
					if (type.startsWith('image/')) {
						const blob = await item.getType(type);
						imageUrl = URL.createObjectURL(blob);
						console.log(`Image URL (${type}): ${imageUrl}`);
					}
				}
			}

			if (imageUrl) {
				files = [
					...files,
					{
						type: 'image',
						url: imageUrl
					}
				];
			}

			text = command.content.replaceAll('{{CLIPBOARD}}', clipboardText);
		}

		prompt = text;

		const chatInputElement = document.getElementById('chat-textarea');

		await tick();

		chatInputElement.style.height = '';
		chatInputElement.style.height = Math.min(chatInputElement.scrollHeight, 200) + 'px';

		chatInputElement?.focus();

		await tick();

		const words = findWordIndices(prompt);

		if (words.length > 0) {
			const word = words.at(0);
			chatInputElement.setSelectionRange(word?.startIndex, word.endIndex + 1);
		}
	};
</script>

{#if filteredPromptCommands.length > 0}
	<div class="pl-1 pr-12 mb-3 text-left w-full absolute bottom-0 left-0 right-0">
		<div class="flex w-full px-2">
			<div class=" bg-gray-100 dark:bg-gray-700 w-10 rounded-l-xl text-center">
				<div class=" text-lg font-semibold mt-2">/</div>
			</div>

			<div class="max-h-60 flex flex-col w-full rounded-r-xl bg-white">
				<div class="m-1 overflow-y-auto p-1 rounded-r-xl space-y-0.5">
					{#each filteredPromptCommands as command, commandIdx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left {commandIdx === selectedCommandIdx
								? ' bg-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmCommand(command);
							}}
							on:mousemove={() => {
								selectedCommandIdx = commandIdx;
							}}
							on:focus={() => {}}
						>
							<div class=" font-medium text-black">
								{command.command}
							</div>

							<div class=" text-xs text-gray-600">
								{command.title}
							</div>
						</button>
					{/each}
				</div>

				<div
					class=" px-2 pb-1 text-xs text-gray-600 bg-white rounded-br-xl flex items-center space-x-1"
				>
					<div>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-3 h-3"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</div>

					<div class="line-clamp-1">
						{$i18n.t(
							'Tip: Update multiple variable slots consecutively by pressing the tab key in the chat input after each replacement.'
						)}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
