<script>
	import { onDestroy, onMount, tick, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Markdown from './Markdown.svelte';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
	import {
		chatId,
		mobile,
		showArtifacts,
		showControls,
		showBottomArtifacts,
		showLeftArtifacts,
		leftHistory,
		bottomHistory,
		isFinishGenRes
	} from '$lib/stores';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Message from './Message.svelte';

	export let id;
	export let content;
	export let model = null;
	export let sources = null;
	export let history = {
		currentId: '',
		messages: {}
	};

	export let save = false;
	export let floatingButtons = true;
	export let onSourceClick = () => {};

	let contentContainerElement;
	let buttonsContainerElement;

	let selectedText = '';
	let floatingInput = false;
	let floatingInputValue = '';

	const updateButtonPosition = (event) => {
		if (
			!contentContainerElement?.contains(event.target) &&
			!buttonsContainerElement?.contains(event.target)
		) {
			closeFloatingButtons();
			return;
		}

		setTimeout(async () => {
			await tick();

			if (!contentContainerElement?.contains(event.target)) return;

			let selection = window.getSelection();

			if (selection.toString().trim().length > 0) {
				floatingInput = false;
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();

				const parentRect = contentContainerElement.getBoundingClientRect();

				// Adjust based on parent rect
				const top = rect.bottom - parentRect.top;
				const left = rect.left - parentRect.left;

				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';

					// Calculate space available on the right
					const spaceOnRight = parentRect.width - (left + buttonsContainerElement.offsetWidth);

					let thirdScreenWidth = window.innerWidth / 3;

					if (spaceOnRight < thirdScreenWidth) {
						const right = parentRect.right - rect.right;
						buttonsContainerElement.style.right = `${right}px`;
						buttonsContainerElement.style.left = 'auto'; // Reset left
					} else {
						// Enough space, position using 'left'
						buttonsContainerElement.style.left = `${left}px`;
						buttonsContainerElement.style.right = 'auto'; // Reset right
					}

					buttonsContainerElement.style.top = `${top + 5}px`; // +5 to add some spacing
				}
			} else {
				closeFloatingButtons();
			}
		}, 0);
	};

	const closeFloatingButtons = () => {
		if (buttonsContainerElement) {
			buttonsContainerElement.style.display = 'none';
			selectedText = '';
			floatingInput = false;
			floatingInputValue = '';
		}
	};

	const selectAskHandler = () => {
		dispatch('select', {
			type: 'ask',
			content: selectedText,
			input: floatingInputValue
		});

		floatingInput = false;
		floatingInputValue = '';
		selectedText = '';

		// Clear selection
		window.getSelection().removeAllRanges();
		buttonsContainerElement.style.display = 'none';
	};

	const keydownHandler = (e) => {
		if (e.key === 'Escape') {
			closeFloatingButtons();
		}
	};

	onMount(() => {
		if (floatingButtons) {
			contentContainerElement?.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('keydown', keydownHandler);
		}
	});

	onDestroy(() => {
		if (floatingButtons) {
			contentContainerElement?.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('keydown', keydownHandler);
		}
	});
	// TODO if we want to clear previous history!
	// $: {
	// 	if (!$isFinishGenRes) {
	// 		bottomHistory.set({
	// 			currentId: '',
	// 			messages: {}
	// 		});
	// 		leftHistory.set({
	// 			currentId: '',
	// 			messages: {}
	// 		});
	// 	}
	// }
</script>

<div bind:this={contentContainerElement}>
	<Markdown
		{id}
		{content}
		{model}
		{save}
		sourceIds={(sources ?? []).reduce((acc, s) => {
			let ids = [];
			s.document.forEach((document, index) => {
				const metadata = s.metadata?.[index];
				const id = metadata?.source ?? 'N/A';

				if (metadata?.name) {
					ids.push(metadata.name);
					return ids;
				}

				if (id.startsWith('http://') || id.startsWith('https://')) {
					ids.push(id);
				} else {
					ids.push(s?.source?.name ?? id);
				}

				return ids;
			});

			acc = [...acc, ...ids];

			// remove duplicates
			return acc.filter((item, index) => acc.indexOf(item) === index);
		}, [])}
		{onSourceClick}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:code={(e) => {
			const { lang, code } = e.detail;
			const { currentId, messages } = history;
			const currentMessage = messages[currentId];

			// Case 1: Check if the message includes 'OpenLeftArtifacts' & 'OpenBottomArtifacts'
			if (currentId && currentMessage.content.includes('OpenAllArtifacts')) {
				console.log('OpenAllArtifacts');
				leftHistory.set({
					currentId,
					messages: {
						...$leftHistory?.messages,
						...Object.fromEntries(
							Object.entries(history.messages).filter(([id, message]) =>
								message.content.includes('OpenAllArtifacts')
							)
						)
					}
				});
				bottomHistory.set({
					currentId,
					messages: {
						...$bottomHistory?.messages,
						...Object.fromEntries(
							Object.entries(history.messages).filter(([id, message]) =>
								message.content.includes('OpenAllArtifacts')
							)
						)
					}
				});
				showLeftArtifacts.set(false);
				showBottomArtifacts.set(false);
				showControls.set(false);
				showArtifacts.set(false);
				setTimeout(() => {
					showLeftArtifacts.set(true);
					showBottomArtifacts.set(true);
					showControls.set(true);
					showArtifacts.set(true);
				}, 200);
			}

			// Case 2: Check if the message includes 'OpenBottomArtifacts'
			else if (currentId && currentMessage.content.includes('OpenBottomArtifacts')) {
				console.log('OpenBottomArtifacts only');
				bottomHistory.set({
					currentId,
					messages: {
						...$bottomHistory?.messages,
						...Object.fromEntries(
							Object.entries(history.messages).filter(([id, message]) =>
								message.content.includes('OpenBottomArtifacts')
							)
						)
					}
				});
				showBottomArtifacts.set(false);
				setTimeout(() => {
					showBottomArtifacts.set(true);
				}, 200);
			}

			// Case 3: Check if the message includes 'OpenLeftArtifacts'
			else if (currentId && currentMessage.content.includes('OpenLeftArtifacts')) {
				console.log('OpenLeftArtifacts only');
				leftHistory.set({
					currentId,
					messages: {
						...$leftHistory?.messages,
						...Object.fromEntries(
							Object.entries(history.messages).filter(([id, message]) =>
								message.content.includes('OpenLeftArtifacts')
							)
						)
					}
				});
				showLeftArtifacts.set(false);
				setTimeout(() => {
					showLeftArtifacts.set(true);
				}, 200);
			}

			// Case 4: Handle html, svg, and xml content for artifacts
			else if (
				currentId &&
				(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
				!$mobile &&
				$chatId &&
				currentMessage.parentId &&
				currentMessage.done
			) {
				console.log('HTML, SVG, XML content');
				showBottomArtifacts.set(false);
				showLeftArtifacts.set(false);
				showArtifacts.set(true);
			}
		}}
	/>
</div>

{#if floatingButtons}
	<div
		bind:this={buttonsContainerElement}
		class="absolute rounded-lg mt-1 text-xs z-[9999]"
		style="display: none"
	>
		{#if !floatingInput}
			<div
				class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl"
			>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={() => {
						selectedText = window.getSelection().toString();
						floatingInput = true;
					}}
				>
					<ChatBubble className="size-3 shrink-0" />

					<div class="shrink-0">Ask</div>
				</button>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={() => {
						const selection = window.getSelection();
						dispatch('select', {
							type: 'explain',
							content: selection.toString()
						});

						// Clear selection
						selection.removeAllRanges();
						buttonsContainerElement.style.display = 'none';
					}}
				>
					<LightBlub className="size-3 shrink-0" />

					<div class="shrink-0">Explain</div>
				</button>
			</div>
		{:else}
			<div
				class="py-1 flex dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border dark:border-gray-800 w-72 rounded-full shadow-xl"
			>
				<input
					type="text"
					class="ml-5 bg-transparent outline-none w-full flex-1 text-sm"
					placeholder={$i18n.t('Ask a question')}
					bind:value={floatingInputValue}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							selectAskHandler();
						}
					}}
				/>

				<div class="ml-1 mr-2">
					<button
						class="{floatingInputValue !== ''
							? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
							: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
						on:click={() => {
							selectAskHandler();
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
			</div>
		{/if}
	</div>
{/if}
