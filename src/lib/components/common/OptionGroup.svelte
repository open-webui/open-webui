<!-- OptionGroup.svelte -->
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import {
		mobile,
	} from '$lib/stores';
    import '$lib/styles/pill-button.css'; // Import the shared styles


    const dispatch = createEventDispatcher();

    export let options = [
        { title: 'Option 1', description: 'Description for option 1', state: 'unselected'},
        { title: 'Option 2', description: 'Description for option 2', state: 'unselected'},
        { title: 'Option 3', description: 'Description for option 3', state: 'unselected'}
    ];

    export let option_context = {header_message: '', footer_message: ''};
    export let optionSelected = false
    export let selectedTitle = ''

    $: _optionSelected = optionSelected;

    function handleClick(option: { title: string, description: string, state: string }) {
        if (option.state === 'selected' || option.state === 'disabled') {
            return;
        } else {
            optionSelected = true;
            selectedTitle = option.title;
            option.state = 'selected';
            dispatch('click', option);
        }
    }
</script>

<div class="option-group">
    {#if option_context.header_message}
        {option_context.header_message}
    {/if}
    {#each options as option}
        <div class="max-w-[max-content] flex items-center">
            <button class="{(_optionSelected && selectedTitle === option.title) || (option.state === 'selected')  ? 'pill-button selected' : (_optionSelected && option.state === 'disabled') ? 'pill-button disabled' : 'pill-button'} rounded-3xl px-5 py-0 flex items-center text-left"
                on:click={() => handleClick(option)}
            >
                {option.title}
            </button>
            {#if !$mobile}
                <span class="{(_optionSelected && selectedTitle === option.title) || (option.state === 'selected') || (option.state === 'unselected') ? 'description' : (_optionSelected || option.state === 'disabled') ? 'description disabled' : 'description'}">
                    {option.description}
                </span>
            {/if}
        </div>
    {/each}
    {#if option_context.footer_message}
        {option_context.footer_message}
    {/if}
</div>

<style>
    .option-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .description {
        margin-left: 0.5rem;
    }
    .description.disabled {
        margin-left: 0.5rem;
        display: none;
    }
</style>