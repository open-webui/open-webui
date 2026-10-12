<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';

	const i18n = getContext('i18n');

	export let onChange: Function = () => {};
	export let state = 'private';
</script>

<div class=" rounded-lg flex flex-col gap-2">
	<div class="">
		<div class=" text-xs font-normal mb-2.5 text-gray-500">{$i18n.t('Visibility')}</div>

		<div class="flex gap-2.5 items-center mb-1">
			<div>
				<div class=" p-2 bg-black/5 dark:bg-white/5 rounded-full">
					{#if state === 'private'}
						<Lock className="w-5 h-5" strokeWidth="1.8" />
					{:else}
						<Hashtag className="w-5 h-5" strokeWidth="1.8" />
					{/if}
				</div>
			</div>

			<div>
				<select
					id="models"
					class="outline-hidden bg-transparent text-sm font-normal block w-fit pr-10 max-w-full placeholder-gray-400"
					value={state === 'private' ? 'private' : 'public'}
					on:change={(e) => {
						if (e.target.value === 'public') {
							state = 'public';
						} else {
							state = 'private';
						}
						onChange(state);
					}}
				>
					<option class=" text-gray-700" value="public" selected>{$i18n.t('Public')}</option>
					<option class=" text-gray-700" value="private" selected>{$i18n.t('Private')}</option>
				</select>

				<div class=" text-xs text-gray-400 font-normal">
					{#if state === 'private'}
						{$i18n.t('Only invited users can access')}
					{:else}
						{$i18n.t('Visible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
