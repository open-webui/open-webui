<script lang="ts">
	import { getContext } from 'svelte';
	import { Popover } from 'bits-ui';
	import type { ChatParticipant } from '$lib/apis/folders';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let participants: ChatParticipant[] = [];
	export let owner: ChatParticipant | null = null;
	export let avatarClass = 'size-4';
	export let activeProfileId: string | null = null;
	export let overflowOpen = false;
	export let mode: 'contributors' | 'presence' = 'contributors';

	// Preserve the base overflow label alongside its generated plural forms.
	// $i18n.t('Show all {{count}} contributors');
	$: people = participants.length
		? participants
		: mode === 'contributors' && owner?.id
			? [owner]
			: [];
	$: if (activeProfileId && !people.some((person) => person.id === activeProfileId)) {
		activeProfileId = null;
	}
	$: if (people.length <= 3) overflowOpen = false;

	const setProfileOpen = (id: string, open: boolean) => {
		if (open) activeProfileId = id;
		else if (activeProfileId === id) activeProfileId = null;
	};
</script>

{#snippet avatar(person: ChatParticipant, className: string)}
	<img
		src="{WEBUI_API_BASE_URL}/users/{person.id}/profile/image"
		alt=""
		draggable="false"
		class="{className} rounded-full shrink-0 object-cover"
		onerror={(event) => {
			const image = event.currentTarget as HTMLImageElement;
			if (!image.src.endsWith('/static/favicon.png')) {
				image.src = `${WEBUI_BASE_URL}/static/favicon.png`;
			}
		}}
	/>
{/snippet}

<div class="flex shrink-0 items-center gap-1" data-chat-participants draggable="false">
	<div
		class="flex items-center {mode === 'presence'
			? '-space-x-2'
			: '-space-x-1'} rtl:space-x-reverse"
	>
		{#each people.slice(0, 3) as person (person.id)}
			<div class="relative rounded-full hover:z-10 focus-within:z-10">
				<ProfilePreview
					side={mode === 'presence' ? 'bottom' : 'right'}
					align={mode === 'presence' ? 'end' : 'center'}
					user={{ id: person.id, name: person.name || $i18n.t('Unknown User') }}
					bind:openPreview={
						() => !overflowOpen && activeProfileId === person.id,
						(open) => setProfileOpen(person.id, open)
					}
				>
					{@render avatar(
						person,
						`${avatarClass} bg-white dark:bg-gray-900 ${
							mode === 'presence'
								? `ring-2 ${['ring-red-400', 'ring-sky-400', 'ring-lime-500', 'ring-amber-400', 'ring-violet-400'][person.id.charCodeAt(0) % 5]}`
								: 'ring-1 ring-white dark:ring-gray-900'
						}`
					)}
				</ProfilePreview>
			</div>
		{/each}
	</div>

	{#if people.length > 3}
		<Popover.Root bind:open={overflowOpen} onOpenChange={() => (activeProfileId = null)}>
			<Popover.Trigger
				class="shrink-0 rounded px-0.5 {mode === 'presence'
					? 'h-6 text-xs'
					: 'text-[0.625rem]'} text-gray-500 hover:bg-gray-100 focus-visible:outline dark:text-gray-400 dark:hover:bg-gray-800"
				aria-label={mode === 'presence'
					? $i18n.t('Collaborators')
					: $i18n.t('Show all {{count}} contributors', { count: people.length })}
			>
				+{people.length - 3}
			</Popover.Trigger>
			<Popover.Portal>
				<Popover.Content
					role="dialog"
					trapFocus={false}
					side="bottom"
					align={mode === 'presence' ? 'end' : 'start'}
					sideOffset={6}
					class="z-[9999] w-60 max-w-[calc(100vw-1.5rem)] max-h-80 overflow-y-auto rounded-xl bg-white p-2 text-gray-900 shadow-lg ring-1 ring-black/5 dark:bg-gray-850 dark:text-gray-100 dark:ring-white/10"
					aria-label={mode === 'presence' ? $i18n.t('Collaborators') : $i18n.t('Contributors')}
				>
					{#if mode === 'presence'}
						<div class="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Collaborators')}
						</div>
					{/if}
					<ul class="space-y-1">
						{#each people as person (person.id)}
							<li
								class="rounded-lg p-1 hover:bg-gray-50 dark:hover:bg-gray-800 [&>button]:max-w-full"
							>
								<ProfilePreview
									side={mode === 'presence' ? 'bottom' : 'right'}
									align={mode === 'presence' ? 'end' : 'center'}
									user={{ id: person.id, name: person.name || $i18n.t('Unknown User') }}
									bind:openPreview={
										() => overflowOpen && activeProfileId === person.id,
										(open) => setProfileOpen(person.id, open)
									}
								>
									{@render avatar(person, 'size-6')}
									<span class="ms-2 min-w-0 truncate text-sm">
										{person.name || $i18n.t('Unknown User')}
									</span>
								</ProfilePreview>
							</li>
						{/each}
					</ul>
				</Popover.Content>
			</Popover.Portal>
		</Popover.Root>
	{/if}
</div>
