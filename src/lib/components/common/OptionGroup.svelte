<!-- OptionGroup.svelte -->
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import {
		mobile,
	} from '$lib/stores';

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
        if (_optionSelected || option.state === 'selected' || option.state === 'disabled') {
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
            <button class="{(_optionSelected && selectedTitle === option.title) || (option.state === 'selected')  ? 'pill-button selected' : (_optionSelected || option.state === 'disabled') ? 'pill-button disabled' : 'pill-button'} rounded-3xl px-5 py-0 flex items-center"
                on:click={() => handleClick(option)}
            >
                {option.title}
            </button>
            {#if !$mobile}
                <span class="{(_optionSelected && selectedTitle === option.title) || (option.state === 'selected')  ? 'description' : (_optionSelected || option.state === 'disabled') ? 'description disabled' : 'description'}">
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
    .pill-button {
        background-color: #EB8486;
        transition: background-color 0.2s ease;
        color: white;
        scale: 95%;
        cursor: pointer;
    }
    .pill-button:hover {
        background-color: #EB5352;
        scale: 105%;
    }
    .pill-button.selected {
        background-color: #EB5352;
        scale: 100%;
        font-weight: bold;
        cursor: default;
    }
    .pill-button.disabled {
        background-color: #aaaaaa;
        color: #7b7b7b;
        scale: 95%;
        cursor: default;
        pointer-events: none;
        display: none;
    }
</style>