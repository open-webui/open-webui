<script>
import { characters, temporaryChatEnabled } from '$lib/stores';
import { formatDate } from '$lib/utils';
import { chats, chatId, user, chatSysPrompt } from '$lib/stores';
import { v4 as uuidv4} from 'uuid';
import { goto } from '$app/navigation';
import { getCharacters } from '$lib/apis/character';
import { onMount } from 'svelte';

console.log('characters', $characters)

onMount(async () => {
    try {
        const charactersFromDB = await getCharacters(localStorage.token)
        console.log('charactersFromDB', charactersFromDB)
        characters.set(charactersFromDB) 
    } catch (error) {
        console.error('Error fetching prompt:', error);
    }
});

function startInterview(characterName, systemPrompt) {
    const newChatId = uuidv4()
    
    console.log('$chats', $chats)
    const newChat = {
        id: newChatId,
        title: `Chat with ${characterName}`, // setting title here is an issue because title will be overriden by when user sends new message in chat
        timestamp: new Date().toISOString(),
        messages: [],
        systemPrompt: systemPrompt,
        model: localStorage.getItem('selectedModel') || 'llama3.2:latest',
        temporary: $temporaryChatEnabled
    }

    chatSysPrompt.set(systemPrompt)

    chats.update(existingChats => {
        return [...existingChats, newChat]
    })

    chatId.set(newChatId)
    goto('/')
}
</script>

<div class="gap-1 my-1.5 pb-1 px-[18px] flex-1 max-h-full overflow-y-auto">
    <div class="text-xl font-medium px-0.5 mb-2">
        <h1>Browse Characters</h1>
    </div>

    <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm">
        <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
            <tr class="">
                <th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
                    <div class="flex gap-1.5 items-center">Character Name</div>
                </th>
                <th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
                    <div class="flex gap-1.5 items-center">Created At</div>
                </th>
                <th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
                    <div class="flex gap-1.5 items-center">System Prompt</div>
                </th>
                <th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
                    <div class="flex gap-1.5 items-center">Interview</div>
                </th>
                <!-- <th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
                    <div class="flex gap-1.5 items-center">Delete</div>
                </th> -->
        </thead>
        <tbody>
            {#each $characters as character}
                <tr>
                    <td class='px-3 py-1'>
                        <div>{character.title}</div>
                    </td>
                    <td class='px-3 py-1'>
                        <div>{formatDate(character.created_at * 1000)}</div> <!--convert from s to ms-->
                    </td>
                    <td class='px-3 py-1'>
                        <div>
                            <!-- TODO: edit and save option for text area-->
                            <textarea class="w-full" 
                            readonly={$user?.role != 'admin'} 
                            value={character.system_prompt}></textarea>
                        </div>
                    </td>
                    <td class='px-3 py-1'>
                        <div>
                            <button 
                                class="px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
                                on:click={() => startInterview(character.character_name, character.system_prompt)}
                            >
                                Start Interview
                            </button>
                        </div>
                    </td>
                </tr>
            {/each}
        </tbody>
</div>