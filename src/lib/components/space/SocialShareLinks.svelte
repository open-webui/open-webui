<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let url: string;
	export let title: string = '';
	export let compact: boolean = false;

	$: encodedUrl = encodeURIComponent(url);
	$: encodedTitle = encodeURIComponent(title);

	$: twitterUrl = `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`;
	$: linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;
	$: emailUrl = `mailto:?subject=${encodedTitle}&body=${encodedUrl}`;
</script>

<div class="flex items-center gap-1.5">
	<a
		href={twitterUrl}
		target="_blank"
		rel="noopener noreferrer"
		class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
		title={$i18n.t('Share on X')}
	>
		<svg class="{compact ? 'size-3.5' : 'size-4'}" viewBox="0 0 24 24" fill="currentColor">
			<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
		</svg>
	</a>

	<a
		href={linkedinUrl}
		target="_blank"
		rel="noopener noreferrer"
		class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-[#0A66C2] transition"
		title={$i18n.t('Share on LinkedIn')}
	>
		<svg class="{compact ? 'size-3.5' : 'size-4'}" viewBox="0 0 24 24" fill="currentColor">
			<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
		</svg>
	</a>

	<a
		href={emailUrl}
		class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
		title={$i18n.t('Share via Email')}
	>
		<svg class="{compact ? 'size-3.5' : 'size-4'}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
			<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
		</svg>
	</a>
</div>
