<script lang="ts">
	import { getContext, setContext, type ComponentType, type SvelteComponent } from 'svelte';
	import { writable } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { config, user, WEBUI_NAME } from '$lib/stores';
	import { type PageContext } from '$lib/utils/page';
	import { pageTabKey } from './tabs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Workspace from '$lib/components/workspace/Workspace.svelte';
	import AutomationsLayout from '$lib/components/automations/AutomationsLayout.svelte';
	import Playground from '$lib/components/playground/Playground.svelte';
	import HomeLayout from '$lib/components/home/HomeLayout.svelte';

	export let href: string;
	export let active = false;
	const visible = writable(active);
	$: visible.set(active);
	export let onNavigate: (href: string) => Promise<void>;
	export let onTitleChange: (title: string) => void;
	const i18n = getContext<any>('i18n');
	const url = writable(new URL(href, location.origin));
	$: url.set(new URL(href, location.origin));
	const beforeLeave: PageContext['beforeLeave'] = new Set();
	export async function requestClose() {
		for (const callback of beforeLeave) if ((await callback()) === false) return false;
		return true;
	}
	async function navigate(target: string | URL, options?: Parameters<typeof goto>[1]) {
		const next = new URL(target, $url);
		if (next.origin !== location.origin || !pageTabKey(next)) return goto(next, options);
		if (next.href === $url.href) return;
		return onNavigate(next.pathname + next.search + next.hash);
	}
	setContext<PageContext>('page', {
		url,
		active: visible,
		goto: navigate,
		beforeLeave,
		setTitle: (title) => {
			for (const brand of [$WEBUI_NAME, 'Open WebUI']) {
				for (const separator of [' / ', ' · ']) {
					if (title.endsWith(separator + brand))
						title = title.slice(0, -(separator + brand).length);
				}
			}
			onTitleChange(title);
		}
	});
	function followLink(event: MouseEvent) {
		if (
			event.defaultPrevented ||
			event.button ||
			event.metaKey ||
			event.ctrlKey ||
			event.shiftKey ||
			event.altKey
		)
			return;
		const link = (event.target as Element).closest<HTMLAnchorElement>('a[href]');
		if (!link || link.target || link.hasAttribute('download')) return;
		const next = new URL(link.href);
		if (next.origin !== location.origin || !pageTabKey(next)) return;
		event.preventDefault();
		void navigate(next);
	}
	const pages: Record<string, () => Promise<{ default: ComponentType<SvelteComponent<any>> }>> = {
		'/channels/:id': () => import('$lib/components/channel/Channel.svelte'),
		'/channels/:id/encrypted': () => import('$lib/components/channel/EncryptedChannel.svelte'),
		'/notes': () => import('$lib/components/notes/NotesPage.svelte'),
		'/notes/new': () => import('$lib/components/notes/CreateNote.svelte'),
		'/notes/:id': () => import('$lib/components/notes/NoteEditor.svelte'),
		'/automations': () => import('$lib/components/automations/Automations.svelte'),
		'/automations/:id': () => import('$lib/components/automations/Automation.svelte'),
		'/calendar': () => import('$lib/components/calendar/Calendar.svelte'),
		'/workspace': () => import('$lib/components/workspace/WorkspaceRedirect.svelte'),
		'/workspace/models': () => import('$lib/components/workspace/Models.svelte'),
		'/workspace/models/create': () => import('$lib/components/workspace/Models/CreateModel.svelte'),
		'/workspace/models/edit': () => import('$lib/components/workspace/Models/EditModel.svelte'),
		'/workspace/knowledge': () => import('$lib/components/workspace/Knowledge.svelte'),
		'/workspace/knowledge/create': () => import('$lib/components/workspace/Knowledge.svelte'),
		'/workspace/knowledge/:id': () =>
			import('$lib/components/workspace/Knowledge/KnowledgeBase.svelte'),
		'/workspace/prompts': () => import('$lib/components/workspace/Prompts.svelte'),
		'/workspace/prompts/create': () => import('$lib/components/workspace/Prompts.svelte'),
		'/workspace/prompts/:id': () => import('$lib/components/workspace/Prompts/EditPrompt.svelte'),
		'/workspace/tools': () => import('$lib/components/workspace/Tools.svelte'),
		'/workspace/tools/create': () => import('$lib/components/workspace/Tools/CreateTool.svelte'),
		'/workspace/tools/edit': () => import('$lib/components/workspace/Tools/EditTool.svelte'),
		'/workspace/skills': () => import('$lib/components/workspace/Skills.svelte'),
		'/workspace/skills/create': () => import('$lib/components/workspace/Skills/CreateSkill.svelte'),
		'/workspace/skills/edit': () => import('$lib/components/workspace/Skills/EditSkill.svelte'),
		'/playground': () => import('$lib/components/playground/Chat.svelte'),
		'/playground/completions': () => import('$lib/components/playground/Completions.svelte'),
		'/playground/images': () => import('$lib/components/playground/Images.svelte'),
		'/home': () => import('$lib/components/home/Home.svelte')
	};
	$: path = $url.pathname.replace(/\/$/, '');
	$: parts = path.split('/');
	$: id = decodeURIComponent(parts[1] === 'workspace' ? (parts[3] ?? '') : (parts[2] ?? ''));
	$: route =
		path in pages
			? path
			: parts[1] === 'workspace'
				? `/workspace/${parts[2]}/:id`
				: `/${parts[1]}/:id${parts[3] === 'encrypted' ? '/encrypted' : ''}`;
	$: key = pageTabKey($url);
	$: props = route.includes(':id')
		? { id }
		: parts[1] === 'workspace' &&
			  parts[3] === 'create' &&
			  ['knowledge', 'prompts'].includes(parts[2])
			? { showCreateOnMount: true, createModalCloseHref: `/workspace/${parts[2]}` }
			: {};
	$: component = key && pages[route as keyof typeof pages]?.();
	$: allowed =
		(parts[1] !== 'notes' ||
			($config?.features?.enable_notes &&
				($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true)))) &&
		(parts[1] !== 'automations' ||
			($config?.features?.enable_automations &&
				($user?.role === 'admin' || $user?.permissions?.features?.automations))) &&
		(parts[1] !== 'calendar' ||
			($config?.features?.enable_calendar &&
				($user?.role === 'admin' || $user?.permissions?.features?.calendar))) &&
		(parts[1] !== 'playground' || $user?.role === 'admin') &&
		(parts[1] !== 'workspace' ||
			!parts[2] ||
			(($user?.role === 'admin' || $user?.permissions?.workspace?.[parts[2]]) &&
				(parts[2] !== 'tools' || $config?.features?.enable_tools)));
</script>

{#snippet content()}
	{#key key}
		{#await component}
			<div class="flex h-full items-center justify-center"><Spinner className="size-5" /></div>
		{:then module}
			{#if module}
				<svelte:component this={module.default} {...props} />
			{:else}
				<div class="p-4">{$i18n.t('Not found')}</div>
			{/if}
		{:catch error}
			<div role="alert" class="p-4">{String(error)}</div>
		{/await}
	{/key}
{/snippet}

<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
<div class="h-full min-h-0 min-w-0 overflow-auto" on:click={followLink}>
	{#if !allowed}
		<div class="p-4 text-sm">{$i18n.t('You do not have permission to access this resource.')}</div>
	{:else if parts[1] === 'workspace'}
		<Workspace>{@render content()}</Workspace>
	{:else if parts[1] === 'automations'}
		<AutomationsLayout>{@render content()}</AutomationsLayout>
	{:else if parts[1] === 'playground'}
		<Playground>{@render content()}</Playground>
	{:else if parts[1] === 'home'}
		<HomeLayout>{@render content()}</HomeLayout>
	{:else}
		{@render content()}
	{/if}
</div>
