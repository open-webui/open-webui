<script lang="ts">
	import { getContext, onMount } from 'svelte';

	import { getBackendConfig } from '$lib/apis';
	import { getFileById } from '$lib/apis/files';
	import { config } from '$lib/stores';

	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';

	const i18n: any = getContext('i18n');

	/** The attached file whose context this sets. */
	export let item: any;
	export let externalKnowledge = false;
	export let onChange: () => void = () => {};

	let loading = true;
	// Files are measured by the backend, which can count tokens.
	let fullText = false;

	const getCharacterCount = (text: string) => Array.from(text).length;

	onMount(async () => {
		if ($config?.file?.full_text_threshold === undefined) {
			await getBackendConfig()
				.then((value) => config.set(value))
				.catch((error) => console.error('Error fetching file context settings:', error));
		}
		if (item?.type === 'file') {
			const file =
				item.file?.full_text === undefined
					? await getFileById(localStorage.token, item.id).catch(() => null)
					: item.file;
			fullText = Boolean(file?.full_text);
		}
		loading = false;
	});

	$: fullTextThreshold = $config?.file?.full_text_threshold ?? 0;
	$: contentLength = getCharacterCount(item?.file?.data?.content ?? '');
	$: automaticFullContent =
		!externalKnowledge &&
		(Boolean($config?.file?.full_context) ||
			fullText ||
			(item?.type === 'text' &&
				$config?.file?.full_text_threshold_type !== 'token' &&
				contentLength > 0 &&
				contentLength <= fullTextThreshold));
	$: enableFullContent = automaticFullContent || item?.context === 'full';
</script>

{#if !loading && $config?.file?.full_text_threshold !== undefined}
	<Tooltip
		content={automaticFullContent
			? $config?.file?.full_context
				? $i18n.t('Full text is always enabled by your administrator.')
				: $i18n.t(
						'This attachment fits within the full text threshold, so its entire text is included automatically.'
					)
			: enableFullContent
				? $i18n.t(
						'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
					)
				: $i18n.t(
						'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
					)}
	>
		<div class="flex items-center gap-1.5 text-xs">
			{$i18n.t('Full text')}
			{#if !automaticFullContent}
				<Switch
					bind:state={enableFullContent}
					ariaLabel={$i18n.t('Full text')}
					on:change={(e) => {
						item.context = e.detail ? 'full' : undefined;
						onChange();
					}}
				/>
			{/if}
		</div>
	</Tooltip>
{/if}
