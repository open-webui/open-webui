<script lang="ts">
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import BarsArrowUp from '$lib/components/icons/BarsArrowUp.svelte';
	import Computer from '$lib/components/icons/Computer.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import QueueList from '$lib/components/icons/QueueList.svelte';
	import SettingsAlt from '$lib/components/icons/SettingsAlt.svelte';
	import SoundHigh from '$lib/components/icons/SoundHigh.svelte';
	import UserCircle from '$lib/components/icons/UserCircle.svelte';
	import WrenchAlt from '$lib/components/icons/WrenchAlt.svelte';

	export let id: string;
	export let className = 'size-3.5';
	export let strokeWidth = '2';
</script>

{#if id === 'general'}
	<SettingsAlt {className} {strokeWidth} />
{:else if id === 'authentication'}
	<Lock {className} {strokeWidth} />
{:else if id === 'connections'}
	<Link {className} {strokeWidth} />
{:else if id === 'models'}
	<svg
		aria-hidden="true"
		xmlns="http://www.w3.org/2000/svg"
		fill="none"
		viewBox="0 0 24 24"
		stroke="currentColor"
		stroke-width={strokeWidth}
		class={className}
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M4 7.5C4 5.57 7.58 4 12 4s8 1.57 8 3.5S16.42 11 12 11 4 9.43 4 7.5Z"
		/>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M4 7.5v4C4 13.43 7.58 15 12 15s8-1.57 8-3.5v-4"
		/>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M4 11.5v4C4 17.43 7.58 19 12 19s8-1.57 8-3.5v-4"
		/>
	</svg>
{:else if id === 'subagents'}
	<UserCircle {className} {strokeWidth} />
{:else if id === 'evaluations'}
	<svg
		aria-hidden="true"
		xmlns="http://www.w3.org/2000/svg"
		fill="none"
		viewBox="0 0 24 24"
		stroke="currentColor"
		stroke-width={strokeWidth}
		class={className}
	>
		<path stroke-linecap="round" stroke-linejoin="round" d="M5 20V10" />
		<path stroke-linecap="round" stroke-linejoin="round" d="M12 20V4" />
		<path stroke-linecap="round" stroke-linejoin="round" d="M19 20v-7" />
	</svg>
{:else if id === 'analytics'}
	<BarsArrowUp {className} {strokeWidth} />
{:else if id === 'integrations'}
	<WrenchAlt {className} {strokeWidth} />
{:else if id === 'documents'}
	<Document {className} {strokeWidth} />
{:else if id === 'web'}
	<GlobeAlt {className} {strokeWidth} />
{:else if id === 'code-execution'}
	<CodeBracket {className} {strokeWidth} />
{:else if id === 'interface'}
	<Computer {className} {strokeWidth} />
{:else if id === 'audio'}
	<SoundHigh {className} {strokeWidth} />
{:else if id === 'images'}
	<Photo {className} {strokeWidth} />
{:else if id === 'pipelines'}
	<QueueList {className} {strokeWidth} />
{:else if id === 'db'}
	<Database {className} {strokeWidth} />
{/if}
