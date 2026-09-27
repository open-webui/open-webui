<script lang="ts">
	import { getContext } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import { thinkingLevel } from '$lib/stores';

	const i18n: any = getContext('i18n');

	let show = false;

	const levels: { id: 'off' | 'none' | 'low' | 'medium' | 'high' | 'max'; label: string; desc: string }[] = [
		{ id: 'off', label: 'Varsayılan', desc: 'Modelin varsayılan ayarını kullan' },
		{ id: 'none', label: 'Kapalı (None)', desc: 'Akıl yürütmeyi zorla kapat (reasoning_effort: none)' },
		{ id: 'low', label: 'Düşük (Low)', desc: 'Hızlı ve temel düzeyde akıl yürütme' },
		{ id: 'medium', label: 'Orta (Medium)', desc: 'Dengeli derin düşünme' },
		{ id: 'high', label: 'Yüksek (High)', desc: 'Kapsamlı ve derinlemesine akıl yürütme' },
		{ id: 'max', label: 'Maksimum (Max)', desc: 'En yüksek akıl yürütme bütçesi (64k token)' }
	];

	const selectLevel = (levelId: 'off' | 'none' | 'low' | 'medium' | 'high' | 'max') => {
		thinkingLevel.set(levelId);
		show = false;
	};
</script>

<Dropdown bind:show>
	<Tooltip content={`Düşünme Seviyesi: ${levels.find((l) => l.id === $thinkingLevel)?.label ?? 'Kapalı'}`} placement="top">
		<button
			type="button"
			id="thinking-menu-button"
			class="relative bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-[1.875rem] flex justify-center items-center outline-hidden focus:outline-hidden shrink-0 transition {$thinkingLevel !== 'off' ? 'text-amber-500 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10' : ''}"
			aria-label="Düşünme Seviyesi"
		>
			<LightBulb className="size-4" strokeWidth={$thinkingLevel !== 'off' ? '2' : '1.5'} />
			{#if $thinkingLevel !== 'off'}
				<span class="absolute -top-0.5 -right-0.5 flex h-2 w-2">
					<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
					<span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
				</span>
			{/if}
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="w-56 p-1">
			<div class="px-2 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800/80 mb-1">
				Düşünme Seviyesi
			</div>
			{#each levels as level}
				<button
					type="button"
					class="w-full flex items-center justify-between px-2.5 py-1.5 text-xs rounded-lg transition hover:bg-gray-100 dark:hover:bg-gray-800/60 {$thinkingLevel === level.id ? 'font-medium text-amber-600 dark:text-amber-400 bg-amber-50/50 dark:bg-amber-950/20' : 'text-gray-700 dark:text-gray-200'}"
					on:click={() => selectLevel(level.id)}
				>
					<div class="flex flex-col text-left">
						<span class="text-xs">{level.label}</span>
						<span class="text-[10px] text-gray-400 dark:text-gray-500">{level.desc}</span>
					</div>
					{#if $thinkingLevel === level.id}
						<Check className="size-3.5 text-amber-500" strokeWidth="2" />
					{/if}
				</button>
			{/each}
		</DropdownMenu>
	</div>
</Dropdown>
