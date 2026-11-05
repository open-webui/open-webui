<script lang="ts">
	import { theme } from '$lib/stores';

	const toggleTheme = () => {
		// Determine the new theme (toggle between light and dark)
		const newTheme = $theme === 'dark' ? 'light' : 'dark';
		
		// Update the store
		theme.set(newTheme);
		
		// Save to localStorage so preference persists
		localStorage.setItem('theme', newTheme);
		
		// Apply the theme to the DOM
		if (newTheme === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	};
</script>

<button
	on:click={toggleTheme}
	class="inline-flex items-center justify-center p-2 rounded-lg 
	       text-gray-600 hover:text-gray-900 hover:bg-gray-100
	       dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-800
	       transition-colors duration-200"
	aria-label={$theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
	title={$theme === 'dark' ? 'Light mode' : 'Dark mode'}
>
	{#if $theme === 'dark'}
		<!-- Sun icon (show when in dark mode to switch to light) -->
		<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
			<path
				fill-rule="evenodd"
				d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zM4.22 4.22a1 1 0 011.414 0l.707.707a1 1 0 00-1.414 1.414l-.707-.707a1 1 0 010-1.414zm11.313 1.414a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM4 10a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zm11-4a4 4 0 11-8 0 4 4 0 018 0zm-1 10a1 1 0 01-1 1H7a1 1 0 110-2h6a1 1 0 011 1z"
				clip-rule="evenodd"
			/>
		</svg>
	{:else}
		<!-- Moon icon (show when in light mode to switch to dark) -->
		<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
			<path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
		</svg>
	{/if}
</button>
