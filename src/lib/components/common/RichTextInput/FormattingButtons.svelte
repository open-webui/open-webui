<script lang="ts">
	import { getContext } from 'svelte';
	import type { Editor } from '@tiptap/core';
	const i18n = getContext<any>('i18n');

	export let editor: Editor | null = null;
	export let onComment: (() => void) | null = null;

	import Bold from '$lib/components/icons/Bold.svelte';
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import H1 from '$lib/components/icons/H1.svelte';
	import H2 from '$lib/components/icons/H2.svelte';
	import H3 from '$lib/components/icons/H3.svelte';
	import Italic from '$lib/components/icons/Italic.svelte';
	import ListBullet from '$lib/components/icons/ListBullet.svelte';
	import NumberedList from '$lib/components/icons/NumberedList.svelte';
	import Strikethrough from '$lib/components/icons/Strikethrough.svelte';
	import Underline from '$lib/components/icons/Underline.svelte';

	import Tooltip from '../Tooltip.svelte';
	import CheckBox from '$lib/components/icons/CheckBox.svelte';
	import ArrowLeftTag from '$lib/components/icons/ArrowLeftTag.svelte';
	import ArrowRightTag from '$lib/components/icons/ArrowRightTag.svelte';

	import EmojiPicker from '../EmojiPicker.svelte';
	import FaceSmile from '$lib/components/icons/FaceSmile.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import { shortCodesToEmojis } from '$lib/stores';

	const headings = [
		{ level: 1 as const, label: 'Heading 1', icon: H1 },
		{ level: 2 as const, label: 'Heading 2', icon: H2 },
		{ level: 3 as const, label: 'Heading 3', icon: H3 }
	];

	let showHeadingMenu = false;
	let headingMenuElement: HTMLElement | null = null;

	// Re-evaluated on every editor transaction, since the parent re-renders with the new editor state.
	$: activeHeading = editor
		? (headings.find((heading) => editor.isActive('heading', { level: heading.level })) ?? null)
		: null;
</script>

<svelte:window
	on:mousedown={(event) => {
		if (
			showHeadingMenu &&
			event.target instanceof Node &&
			!headingMenuElement?.contains(event.target)
		) {
			showHeadingMenu = false;
		}
	}}
	on:keydown={(event) => {
		if (event.key === 'Escape' && showHeadingMenu) showHeadingMenu = false;
	}}
/>

<div
	class="flex gap-0.5 p-0.5 rounded-xl shadow-lg bg-white text-base-800 dark:text-white dark:bg-base-850 min-w-fit border border-base-100 dark:border-base-800"
>
	{#if onComment}
		<Tooltip placement="top" content={$i18n.t('Comment')}>
			<button
				aria-label={$i18n.t('Comment')}
				on:mousedown|preventDefault
				on:click={() => onComment?.()}
				class="hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<Annotation className="size-4" />
			</button>
		</Tooltip>
		<div class="my-1 w-px bg-base-100 dark:bg-base-800" aria-hidden="true"></div>
	{/if}

	<div class="relative flex" bind:this={headingMenuElement}>
		<Tooltip placement="top" content={$i18n.t('Heading')}>
			<button
				aria-label={$i18n.t('Heading')}
				aria-haspopup="menu"
				aria-expanded={showHeadingMenu}
				on:mousedown|preventDefault
				on:click={() => (showHeadingMenu = !showHeadingMenu)}
				class="{activeHeading || showHeadingMenu
					? 'bg-base-50 dark:bg-base-700'
					: ''} flex items-center gap-0.5 hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				{#if activeHeading}
					<svelte:component this={activeHeading.icon} />
				{:else}
					<span class="flex size-4 items-center justify-center text-sm font-medium leading-none"
						>T</span
					>
				{/if}
				<ChevronDown className="size-3" strokeWidth="2" />
			</button>
		</Tooltip>

		{#if showHeadingMenu}
			<div
				role="menu"
				class="absolute left-0 top-full mt-1 z-10 flex min-w-36 flex-col gap-0.5 p-1 rounded-xl shadow-lg bg-white text-base-800 dark:text-white dark:bg-base-850 border border-base-100 dark:border-base-800"
			>
				<button
					role="menuitemradio"
					aria-checked={!activeHeading}
					on:mousedown|preventDefault
					on:click={() => {
						editor?.chain().focus().setParagraph().run();
						showHeadingMenu = false;
					}}
					class="{!activeHeading
						? 'bg-base-50 dark:bg-base-700'
						: ''} flex items-center gap-2 px-2 py-1 rounded-lg text-sm hover:bg-base-50 dark:hover:bg-base-700 transition-all"
					type="button"
				>
					<span class="flex size-4 items-center justify-center text-sm font-medium leading-none"
						>T</span
					>
					{$i18n.t('Text')}
				</button>
				{#each headings as heading}
					<button
						role="menuitemradio"
						aria-checked={activeHeading?.level === heading.level}
						on:mousedown|preventDefault
						on:click={() => {
							editor?.chain().focus().toggleHeading({ level: heading.level }).run();
							showHeadingMenu = false;
						}}
						class="{activeHeading?.level === heading.level
							? 'bg-base-50 dark:bg-base-700'
							: ''} flex items-center gap-2 px-2 py-1 rounded-lg text-sm hover:bg-base-50 dark:hover:bg-base-700 transition-all"
						type="button"
					>
						<svelte:component this={heading.icon} />
						<!-- localisation keys for heading.label to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Heading 1')}
							{$i18n.t('Heading 2')}
							{$i18n.t('Heading 3')}
							{$i18n.t('H1')}
							{$i18n.t('H2')}
							{$i18n.t('H3')}
						-->
						{$i18n.t(heading.label)}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	{#if editor?.isActive('bulletList') || editor?.isActive('orderedList') || editor?.isActive('taskList')}
		<Tooltip placement="top" content={$i18n.t('Lift List')}>
			<button
				aria-label={$i18n.t('Lift List')}
				on:click={() => {
					editor?.commands.liftListItem(editor?.isActive('taskList') ? 'taskItem' : 'listItem');
				}}
				class="hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<ArrowLeftTag />
			</button>
		</Tooltip>
		<Tooltip placement="top" content={$i18n.t('Sink List')}>
			<button
				aria-label={$i18n.t('Sink List')}
				on:click={() =>
					editor?.commands.sinkListItem(editor?.isActive('taskList') ? 'taskItem' : 'listItem')}
				class="hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<ArrowRightTag />
			</button>
		</Tooltip>
	{/if}

	<Tooltip placement="top" content={$i18n.t('Bullet List')}>
		<button
			aria-label={$i18n.t('Bullet List')}
			aria-pressed={editor?.isActive('bulletList')}
			on:click={() => editor?.chain().focus().toggleBulletList().run()}
			class="{editor?.isActive('bulletList')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<ListBullet />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Ordered List')}>
		<button
			aria-label={$i18n.t('Ordered List')}
			aria-pressed={editor?.isActive('orderedList')}
			on:click={() => editor?.chain().focus().toggleOrderedList().run()}
			class="{editor?.isActive('orderedList')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<NumberedList />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Task List')}>
		<button
			aria-label={$i18n.t('Task List')}
			aria-pressed={editor?.isActive('taskList')}
			on:click={() => editor?.chain().focus().toggleTaskList().run()}
			class="{editor?.isActive('taskList')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<CheckBox />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Bold')}>
		<button
			aria-label={$i18n.t('Bold')}
			aria-pressed={editor?.isActive('bold')}
			on:click={() => editor?.chain().focus().toggleBold().run()}
			class="{editor?.isActive('bold')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Bold />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Italic')}>
		<button
			aria-label={$i18n.t('Italic')}
			aria-pressed={editor?.isActive('italic')}
			on:click={() => editor?.chain().focus().toggleItalic().run()}
			class="{editor?.isActive('italic')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Italic />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Underline')}>
		<button
			aria-label={$i18n.t('Underline')}
			aria-pressed={editor?.isActive('underline')}
			on:click={() => editor?.chain().focus().toggleUnderline().run()}
			class="{editor?.isActive('underline')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Underline />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Strikethrough')}>
		<button
			aria-label={$i18n.t('Strikethrough')}
			aria-pressed={editor?.isActive('strike')}
			on:click={() => editor?.chain().focus().toggleStrike().run()}
			class="{editor?.isActive('strike')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Strikethrough />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Code Block')}>
		<button
			aria-label={$i18n.t('Code Block')}
			aria-pressed={editor?.isActive('codeBlock')}
			on:click={() => editor?.chain().focus().toggleCodeBlock().run()}
			class="{editor?.isActive('codeBlock')
				? 'bg-base-50 dark:bg-base-700'
				: ''} hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<CodeBracket />
		</button>
	</Tooltip>

	<EmojiPicker
		onSubmit={(shortCode) => {
			const codepoint: string | undefined = ($shortCodesToEmojis as Record<string, string>)[
				shortCode
			];
			if (codepoint) {
				const emoji = codepoint
					.split('-')
					.map((cp: string) => String.fromCodePoint(parseInt(cp, 16)))
					.join('');
				editor?.chain().focus().insertContent(emoji).run();
			}
		}}
	>
		<Tooltip placement="top" content={$i18n.t('Emoji')}>
			<button
				aria-label={$i18n.t('Emoji')}
				class="hover:bg-base-50 dark:hover:bg-base-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<FaceSmile className="size-4" />
			</button>
		</Tooltip>
	</EmojiPicker>
</div>
