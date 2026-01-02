<script>
	/**
	 * TooltipButton - 재사용 가능한 툴팁 메뉴 버튼 컴포넌트
	 *
	 * 사용법:
	 * <TooltipButton label="로그아웃" on:click={handleLogout}>
	 *   <LogoutIcon slot="icon" />
	 * </TooltipButton>
	 *
	 * <TooltipButton label="응답 스타일" hasSubmenu on:click={toggleSubmenu}>
	 *   <StyleIcon slot="icon" />
	 * </TooltipButton>
	 *
	 * <TooltipButton label="다크 모드" variant="toggle">
	 *   <MoonIcon slot="icon" />
	 * </TooltipButton>
	 */

	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	// Props
	export let label = '';
	export let variant = 'default'; // 'default' | 'toggle'
	export let hasSubmenu = false;
	export let active = false;
	export let disabled = false;
	export let className = '';

	function handleClick(e) {
		if (!disabled) {
			dispatch('click', e);
		}
	}
</script>

<!-- Default variant: icon + label + optional chevron -->
{#if variant === 'default'}
	<button
		class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-xl
			text-caption text-gray-900 dark:text-[#FDFEFE]
			hover:bg-[rgba(113,122,143,0.3)] transition cursor-pointer
			disabled:opacity-50 disabled:cursor-not-allowed
			{active ? 'bg-[rgba(113,122,143,0.3)]' : ''}
			{hasSubmenu ? 'justify-between' : ''}
			{className}"
		on:click={handleClick}
		{disabled}
	>
		<div class="flex items-center gap-2">
			<!-- Icon slot -->
			<div class="w-5 h-5 flex items-center justify-center">
				<slot name="icon" />
			</div>
			<!-- Label -->
			<span class="leading-[18px]">{label}</span>
		</div>

		<!-- Chevron for submenu -->
		{#if hasSubmenu}
			<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
				<path
					d="M7.5 5L12.5 10L7.5 15"
					class="stroke-current"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			</svg>
		{/if}
	</button>

<!-- Toggle variant: circular icon button + label -->
{:else if variant === 'toggle'}
	<button
		class="flex flex-row items-center gap-2 w-full h-7
			bg-gray-200/50 dark:bg-[rgba(39,40,44,0.2)] rounded-full px-0
			hover:bg-gray-300/50 dark:hover:bg-[rgba(39,40,44,0.4)]
			transition cursor-pointer
			disabled:opacity-50 disabled:cursor-not-allowed
			{className}"
		on:click={handleClick}
		{disabled}
	>
		<!-- Circular icon container -->
		<div
			class="w-7 h-7 flex items-center justify-center rounded-full
				bg-gray-300 dark:bg-[#27282C]
				shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_10px_rgba(255,255,255,0.05),inset_2px_2px_16px_rgba(206,212,229,0.12)]
				backdrop-blur-[10px]"
		>
			<slot name="icon" />
		</div>
		<!-- Label -->
		<span class="text-caption text-gray-900 dark:text-[#FDFEFE] leading-[18px]">{label}</span>
	</button>
{/if}

<style>
	/* Additional styles if needed */
</style>
