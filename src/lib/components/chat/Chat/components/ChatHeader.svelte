<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import type { ChatState, ChatHistory } from '../types';
	
	export let chatId: string;
	export let title: string;
	export let selectedModels: string[];
	export let history: ChatHistory;
	export let params: any = {};
	export let shareEnabled = false;
	export let showBanners = true;
	export let initNewChat: () => void;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	
	$: chat = {
		id: chatId,
		chat: {
			title: title,
			models: selectedModels,
			system: params.system,
			params: params,
			history: history,
			timestamp: Date.now()
		}
	};
</script>

<Navbar
	{chat}
	{history}
	{title}
	bind:selectedModels
	{shareEnabled}
	{initNewChat}
	{showBanners}
/>