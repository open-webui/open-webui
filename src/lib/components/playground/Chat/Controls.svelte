<script lang="ts">
	import { getContext } from 'svelte';

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n') as any;

	export let params: any = {};

	const getOpen = (key: string, fallback = true): boolean => {
		const v =
			typeof localStorage !== 'undefined'
				? localStorage.getItem(`playgroundChatControls.${key}`)
				: null;
		return v !== null ? v === 'true' : fallback;
	};

	const setOpen = (key: string) => (open: boolean) => {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(`playgroundChatControls.${key}`, String(open));
		}
	};

	let showValves = getOpen('valves', false);
	let showAdvancedParams = getOpen('advancedParams');
</script>

<div class="dark:text-white">
	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class="dark:text-gray-200 text-sm py-0.5 px-0.5">
			{#if $user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true)}
				<Collapsible
					bind:open={showValves}
					onChange={setOpen('valves')}
					title={$i18n.t('Valves')}
					buttonClassName="w-full"
				>
					<div class="text-sm" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<Collapsible
					title={$i18n.t('Advanced Params')}
					bind:open={showAdvancedParams}
					onChange={setOpen('advancedParams')}
					buttonClassName="w-full"
				>
					<div class="text-sm mt-1.5" slot="content">
						<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
					</div>
				</Collapsible>
			{/if}
		</div>
	{/if}
</div>
