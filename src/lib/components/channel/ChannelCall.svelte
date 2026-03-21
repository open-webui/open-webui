<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import { showSidebar } from '$lib/stores';
	import { getChannelById } from '$lib/apis/channels';

	import Navbar from './ChannelCall/Navbar.svelte';
	import Controls from './ChannelCall/Controls.svelte';
	import Connection from './ChannelCall/Connection.svelte';

	export let id = '';

	let channel = null;
	let enableVideo = true;
	let enableAudio = true;

	$: if (id) {
		initHandler();
	}

	const initHandler = async () => {
		channel = await getChannelById(localStorage.token, id).catch(() => null);
	};
</script>

<svelte:head>
	<title>{channel?.name ? `${channel.name} — Call` : 'Call'} • Open WebUI</title>
</svelte:head>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} w-full max-w-full flex flex-col"
	id="call-container"
>
	<Navbar {channel} />

	<div class="flex-1 min-h-0">
		<Connection channelId={id} {enableVideo} {enableAudio} />
	</div>

	<Controls
		videoEnabled={enableVideo}
		audioEnabled={enableAudio}
		onToggleVideo={(v) => (enableVideo = v)}
		onToggleAudio={(a) => (enableAudio = a)}
		onHangup={() => goto(`/channels/${id}`)}
	/>
</div>
