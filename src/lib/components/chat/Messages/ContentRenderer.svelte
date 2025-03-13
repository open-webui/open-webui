<script>
	import { onDestroy, onMount, tick, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Markdown from './Markdown.svelte';
	import {
		chatId,
		mobile,
		showArtifacts,
		showControls,
		showOverview,
		showBottomArtifacts,
		showLeftArtifacts,
		leftHistory,
		bottomHistory,
		isFinishGenRes
	} from '$lib/stores';
	import FloatingButtons from '../ContentRenderer/FloatingButtons.svelte';
	import { createMessagesList } from '$lib/utils';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
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
	export let onAddMessages = () => {};

	let contentContainerElement;

	let floatingButtonsElement;

	const updateButtonPosition = (event) => {
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
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
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();

				const parentRect = contentContainerElement.getBoundingClientRect();

				// Adjust based on parent rect
				const top = rect.bottom - parentRect.top;
				const left = rect.left - parentRect.left;

				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';

					// Calculate space available on the right
					const spaceOnRight = parentRect.width - left;
					let halfScreenWidth = $mobile ? window.innerWidth / 2 : window.innerWidth / 3;

					if (spaceOnRight < halfScreenWidth) {
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
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
		if (buttonsContainerElement) {
			buttonsContainerElement.style.display = 'none';
		}

		if (floatingButtonsElement) {
			floatingButtonsElement.closeHandler();
		}
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

	$: {
		let last_message = history.messages[history.currentId];
		if (last_message && $isFinishGenRes) {
			if (last_message && last_message.content.includes('OpenAllArtifacts')) {
				showLeftArtifacts.set(true);
				showBottomArtifacts.set(true);
				showArtifacts.set(true);
			} else if (last_message && last_message.content.includes('OpenBottomArtifacts')) {
				showBottomArtifacts.set(true);
			} else if (last_message && last_message.content.includes('OpenLeftArtifacts')) {
				showLeftArtifacts.set(true);
			} else if (last_message && last_message.content.includes('OpenArtifacts')) {
				showControls.set(true);
				showArtifacts.set(true);
			}
		}
	}

	console.log(8888, $showArtifacts, $showControls);
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
		{history}
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

			// Case 1: Check if the message includes 'OpenBottomArtifacts'
			if (currentId && currentMessage.content.includes('OpenBottomArtifacts')) {
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

			// Case 2: Check if the message includes 'OpenLeftArtifacts'
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

			// Case 3: Check if the message includes 'OpenArtifacts'
			else if (currentId && currentMessage.content.includes('OpenArtifacts')) {
				console.log('OpenArtifacts only');
				bottomHistory.set({
					currentId,
					messages: {
						...$bottomHistory?.messages,
						...Object.fromEntries(
							Object.entries(history.messages).filter(([id, message]) =>
								message.content.includes('OpenArtifacts')
							)
						)
					}
				});
				showControls.set(false);
				showArtifacts.set(false);
				setTimeout(() => {
					showControls.set(true);
					showArtifacts.set(true);
				}, 200);
			}

			// Case 5: Handle html, svg, and xml content for artifacts
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
				showControls.set(true);
				showArtifacts.set(true);
			}
		}}
	/>
</div>

{#if floatingButtons && model}
	<FloatingButtons
		bind:this={floatingButtonsElement}
		{id}
		model={model?.id}
		messages={createMessagesList(history, id)}
		onAdd={({ modelId, parentId, messages }) => {
			console.log(modelId, parentId, messages);
			onAddMessages({ modelId, parentId, messages });
			closeFloatingButtons();
		}}
	/>
{/if}
