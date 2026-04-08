<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, showSidebar, isInstructor } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let activeMode: 'chat' | 'dashboard' | 'student' = 'chat';
	export let iconOnly = false;

	const dispatch = createEventDispatcher();

	const handleToggle = (mode: 'chat' | 'dashboard' | 'student') => {
		if (mode === activeMode) return;

		if (mode === 'dashboard') {
			goto('/dashboard');
		} else if (mode === 'student') {
			goto('/me');
		} else {
			// Auto-expand sidebar when returning to chat
			showSidebar.set(true);
			goto('/');
		}
		dispatch('toggle');
	};
</script>

<!-- Tab Button Container -->
<div
	class="box-border flex flex-row justify-center items-center p-0

		bg-[rgba(253,254,254,0.5)] dark:bg-[rgba(39,40,44,0.2)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_10px_rgba(255,255,255,0.05),inset_2px_2px_16px_rgba(206,212,229,0.12)]
		backdrop-blur-[10px] rounded-full"
>
	<!-- Dashboard/Instructor Mode Button (instructors only) -->
	{#if isInstructor($user)}
		<Tooltip content="교수 모드" placement="top">
			<button
				class="flex flex-row justify-center items-center rounded-full transition-all duration-200
					{iconOnly ? 'p-2' : 'py-2 px-4 gap-1'}
					{activeMode === 'dashboard' ? 'bg-[#076EF4]' : 'bg-transparent'}"
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
				{#if !iconOnly}
					<span
						class="text-caption {activeMode === 'dashboard'
							? 'text-[#FDFEFE]'
							: 'text-gray-600 dark:text-gray-400'}"
					>
						교수 모드
					</span>
				{/if}
			</button>
		</Tooltip>
	{/if}

	<!-- Student Personal Dashboard Button -->
	<Tooltip content="내 학습" placement="top">
		<button
			class="flex flex-row justify-center items-center rounded-full transition-all duration-200
				{iconOnly ? 'p-2' : 'py-2 px-4 gap-1'}
				{activeMode === 'student' ? 'bg-[#076EF4]' : 'bg-transparent'}"
			on:click={() => handleToggle('student')}
			aria-label="내 학습"
		>
			<!-- Person Icon -->
			<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
				<mask id="mask_person" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
					<rect width="20" height="20" fill="#D9D9D9"/>
				</mask>
				<g mask="url(#mask_person)">
					<path d="M10 10C9.08333 10 8.29167 9.67361 7.625 9.02083C6.95833 8.36806 6.625 7.58333 6.625 6.66667C6.625 5.75 6.95833 4.96528 7.625 4.3125C8.29167 3.65972 9.08333 3.33333 10 3.33333C10.9167 3.33333 11.7083 3.65972 12.375 4.3125C13.0417 4.96528 13.375 5.75 13.375 6.66667C13.375 7.58333 13.0417 8.36806 12.375 9.02083C11.7083 9.67361 10.9167 10 10 10ZM3.33333 16.6667V14.5C3.33333 14.0139 3.46528 13.5694 3.72917 13.1667C3.99306 12.7639 4.34722 12.4583 4.79167 12.25C5.76389 11.8194 6.75 11.4931 7.75 11.2708C8.75 11.0486 9.36944 10.9375 10 10.9375C10.6306 10.9375 11.25 11.0486 12.25 11.2708C13.25 11.4931 14.2361 11.8194 15.2083 12.25C15.6528 12.4583 16.0069 12.7639 16.2708 13.1667C16.5347 13.5694 16.6667 14.0139 16.6667 14.5V16.6667H3.33333Z" fill={activeMode === 'student' ? '#FDFEFE' : '#8D96AD'}/>
				</g>
			</svg>
			{#if !iconOnly}
				<span
					class="text-caption {activeMode === 'student'
						? 'text-[#FDFEFE]'
						: 'text-gray-600 dark:text-gray-400'}"
				>
					내 학습
				</span>
			{/if}
		</button>
	</Tooltip>

	<!-- Chat Mode Button -->
	<Tooltip content="채팅" placement="top">
		<button
			class="flex flex-row justify-center items-center rounded-full transition-all duration-200
				{iconOnly ? 'p-2' : 'py-2 px-4 gap-1'}
				{activeMode === 'chat' ? 'bg-[#076EF4]' : 'bg-transparent'}"
			on:click={() => handleToggle('chat')}
			aria-label="채팅"
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
			{#if !iconOnly}
				<span
					class="text-caption {activeMode === 'chat'
						? 'text-[#FDFEFE]'
						: 'text-gray-600 dark:text-gray-400'}"
				>
					채팅
				</span>
			{/if}
		</button>
	</Tooltip>
</div>

<style>
	button {
		-webkit-tap-highlight-color: transparent;
	}
</style>
