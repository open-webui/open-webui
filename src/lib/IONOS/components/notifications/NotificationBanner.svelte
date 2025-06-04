<script lang="ts">
	import { fly } from 'svelte/transition';
	import Heart from '$lib/IONOS/components/icons/Heart.svelte';
	import XMark from '$lib/IONOS/components/icons/XMark.svelte';
	import EmojiSad from '$lib/IONOS/components/icons/EmojiSad.svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import { NotificationType, type Notification } from '$lib/IONOS/stores/notifications';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	export let notification: Notification;
</script>

<div transition:fly={{ y: -200, duration: 50 }} class="ease-in-out w-full p-4 sm:p-5 flex items-center justify-start text-sm gap-2 {notification.type}">
	<div id="notification-icon" class="self-start pt-0.5 sm:pt-0">
		{#if notification.type === NotificationType.FEEDBACK}
			<Heart />
		{:else if notification.type === NotificationType.ERROR}
			<EmojiSad className="text-red-500"/>
		{/if}
	</div>
	<div class="flex flex-col md:flex-row gap-2.5 items-start">
		<p>
			<span class="font-semibold">{notification.title}</span>
		 	{notification.message}
		</p>
		{#each notification.actions as action}
			<Link href={action.href ?? ''} className="text-blue-600 underline" on:click={action.handler}>
				{action.label}
			</Link>
		{/each}
	</div>
	{#if notification.dismissible}
		<button class="ml-auto hover:text-red-500 active:text-red-400" on:click={() => dispatch('dismiss', { notification })}>
			<XMark />
		</button>
	{/if}
</div>
