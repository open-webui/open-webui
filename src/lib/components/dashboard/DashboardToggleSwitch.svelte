<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';

	export let activeMode: 'chat' | 'dashboard' = 'chat';

	const dispatch = createEventDispatcher();

	const handleToggle = (mode) => {
		if (mode === activeMode) return;

		if (mode === 'dashboard') {
			goto('/dashboard');
		} else {
			// Auto-expand sidebar when returning to chat
			showSidebar.set(true);
			goto('/');
		}
		dispatch('toggle');
	};

	// Reusable styles
	const containerStyle = `box-border flex flex-row items-center p-0
		w-[260px] h-7
		bg-[rgba(39,40,44,0.2)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_16px_rgba(206,212,229,0.1)]
		backdrop-blur-[10px] rounded-full`;

	const buttonBase = `flex flex-row justify-center items-center px-4 py-1 gap-1
		flex-1 h-7 rounded-full transition-all duration-200`;

	const buttonActive = `${buttonBase} bg-[#076EF4]`;
	const buttonInactive = `${buttonBase} bg-transparent hover:bg-[rgba(255,255,255,0.1)]`;
</script>

<div class={containerStyle}>
	<!-- Dashboard/Instructor Mode Button -->
	<button
		class={activeMode === 'dashboard' ? buttonActive : buttonInactive}
		on:click={() => handleToggle('dashboard')}
		aria-label="교수 모드"
	>
		<!-- School Icon -->
		<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
			<mask id="mask_school" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
				<rect width="20" height="20" fill="#D9D9D9"/>
			</mask>
			<g mask="url(#mask_school)">
				<path d="M10 11.1458L14.1667 8.85417V11.5417C14.1667 11.8889 14.0729 12.2049 13.8854 12.4896C13.6979 12.7743 13.4444 13.0069 13.125 13.1875L10 15L6.875 13.1875C6.55556 13.0069 6.30208 12.7743 6.11458 12.4896C5.92708 12.2049 5.83333 11.8889 5.83333 11.5417V8.85417L10 11.1458ZM10 9.5L3.33333 5.83333L10 2.16667L16.6667 5.83333V11.25H15.4167V6.52083L10 9.5Z" fill={activeMode === 'dashboard' ? '#FDFEFE' : '#8D96AD'}/>
			</g>
		</svg>
		<span class="text-caption {activeMode === 'dashboard' ? 'text-[#FDFEFE]' : 'text-[#8D96AD]'}">교수 모드</span>
	</button>

	<!-- Chat/Student Mode Button -->
	<button
		class={activeMode === 'chat' ? buttonActive : buttonInactive}
		on:click={() => handleToggle('chat')}
		aria-label="학생 모드"
	>
		<!-- Edit Square Icon -->
		<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
			<mask id="mask_edit" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
				<rect width="20" height="20" fill="#D9D9D9"/>
			</mask>
			<g mask="url(#mask_edit)">
				<path d="M4.5 15.5H5.4375L12.8958 8.04167L11.9583 7.10417L4.5 14.5625V15.5ZM15.4583 7.0625L12.9375 4.58333L13.875 3.64583C14.0972 3.42361 14.3715 3.3125 14.6979 3.3125C15.0243 3.3125 15.2986 3.42361 15.5208 3.64583L16.3542 4.47917C16.5764 4.70139 16.6875 4.97222 16.6875 5.29167C16.6875 5.61111 16.5764 5.88542 16.3542 6.11458L15.4583 7.0625ZM14.5 8.02083L5.52083 17H3V14.4792L11.9792 5.5L14.5 8.02083Z" fill={activeMode === 'chat' ? '#FDFEFE' : '#8D96AD'}/>
			</g>
		</svg>
		<span class="text-caption {activeMode === 'chat' ? 'text-[#FDFEFE]' : 'text-[#8D96AD]'}">학생 모드</span>
	</button>
</div>

<style>
	button {
		-webkit-tap-highlight-color: transparent;
	}
</style>
