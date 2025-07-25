<!--
	MessageInput.svelte - Legacy wrapper for backward compatibility
	
	This component has been refactored into smaller, more maintainable components.
	All functionality is now in MessageInput/MessageInput.svelte
	
	This file maintains backward compatibility for existing imports.
-->
<script lang="ts">
	import MessageInput from './MessageInput/MessageInput.svelte';
	
	// Export all props to maintain compatibility
	export let transparentBackground = false;
	export let onChange = () => {};
	export let createMessagePair;
	export let stopResponse;
	export let autoScroll = false;
	export let atSelectedModel = undefined;
	export let selectedModels = [''];
	export let history = {};
	export let taskIds = null;
	export let prompt = '';
	export let files = [];
	export let toolServers = [];
	export let selectedToolIds = [];
	export let selectedFilterIds = [];
	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;
	export let codeInterpreterEnabled = false;
	export let showCommands = false;
	export let placeholder = '';
	
	// Reference to the refactored component
	let messageInput;
	
	// Forward public methods
	export const setText = (text) => messageInput?.setText(text);
</script>

<MessageInput
	bind:this={messageInput}
	{transparentBackground}
	{onChange}
	{createMessagePair}
	{stopResponse}
	{autoScroll}
	{atSelectedModel}
	bind:selectedModels
	{history}
	{taskIds}
	bind:prompt
	bind:files
	{toolServers}
	bind:selectedToolIds
	bind:selectedFilterIds
	bind:imageGenerationEnabled
	bind:webSearchEnabled
	bind:codeInterpreterEnabled
	bind:showCommands
	{placeholder}
	on:submit
	on:keydown
	on:focus
	on:blur
/>