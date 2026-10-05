<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_BUILD_CHANNEL, WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import Tooltip from './Tooltip.svelte';

	const i18n: any = getContext('i18n');
</script>

<Tooltip content={WEBUI_BUILD_HASH}>
	v{WEBUI_VERSION}{#if WEBUI_BUILD_CHANNEL === 'dev'}
		({WEBUI_BUILD_HASH ? `dev · ${WEBUI_BUILD_HASH.slice(0, 9)}` : $i18n.t('dev build')})
	{:else if WEBUI_BUILD_CHANNEL !== 'main'}
		({WEBUI_BUILD_HASH
			? $i18n.t('build · {{hash}}', { hash: WEBUI_BUILD_HASH.slice(0, 9) })
			: $i18n.t('unknown build')})
	{/if}
</Tooltip>
