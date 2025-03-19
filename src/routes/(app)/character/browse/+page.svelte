<script>
import { characters, temporaryChatEnabled } from '$lib/stores';
import { formatDate } from '$lib/utils';
import { chats, chatId, user, chatSysPrompt } from '$lib/stores';
import { v4 as uuidv4} from 'uuid';
import { goto } from '$app/navigation';
import { getCharacters, deleteCharacterById, updateCharacterById } from '$lib/apis/character';
import { onMount } from 'svelte';
import Tooltip from '$lib/components/common/Tooltip.svelte';
import { toast } from 'svelte-sonner';
import Pencil from '$lib/components/icons/Pencil.svelte';
import Modal from '$lib/components/common/Modal.svelte';

let show = false;
let selectedCharacter = {}

onMount(async () => {
    try {
        const charactersFromDB = await getCharacters(localStorage.token)
        console.log('charactersFromDB', charactersFromDB)
        characters.set(charactersFromDB) 
    } catch (error) {
        console.error('Error fetching prompt:', error);
    }
});

const deleteChatHandler = async (characterId) => {
    await deleteCharacterById(localStorage.token, characterId).catch((error) => {
        console.error(error)
        toast.error(`${error}`);
    });

    const charactersFromDB = await getCharacters(localStorage.token)
    characters.set(charactersFromDB)
}

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

const saveCharacter = async (character) => {
    await updateCharacterById(localStorage.token, character.id, character)
    .catch((error) => {
        console.error(error)
        toast.error(`${error}`);
    });

    const charactersFromDB = await getCharacters(localStorage.token)
    characters.set(charactersFromDB)

    show = false
}

</script>

<Modal size="lg" bind:show>
    <div class="text-gray-700 dark:text-gray-100">
		<div class="dark:text-gray-300 px-5 pt-4 pb-4">
			<div>
                <div class="my-2.5 mb-3 text-sm font-medium">Editing System Prompt for {selectedCharacter.title} </div> 
                <textarea class="mt-3 w-full rounded-lg p-4 text-sm bg-white dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-none"
                rows="16"
                bind:value={selectedCharacter.system_prompt}
                ></textarea>
            </div>
            <div class='flex justify-end pt-3 text-sm font-medium'>
                <button 
                    class="px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
                    on:click={() => saveCharacter(selectedCharacter)}
                >
                Save
                </button>
            </div>
	</div>
</Modal>

<div class="gap-1 my-1.5 pb-1 px-[18px] flex-1 max-h-full overflow-y-auto">
    <div class="text-xl font-medium px-0.5 mb-5">
        <h1>Browse Characters</h1>
    </div>

    <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm">
        <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
            <tr class="">
                <th scope="col" class="px-3 py-1.5 select-none">
                    <div class="flex gap-1.5 items-center">Character Name</div>
                </th>
                <th scope="col" class="px-3 py-1.5 select-none">
                    <div class="flex gap-1.5 items-center">Last Updated</div>
                </th>
                <th scope="col" class="px-3 py-1.5 select-none">
                    <div class="flex gap-1.5 items-center">System Prompt</div>
                </th>
                <th scope="col" class="px-5 py-1.5 select-none">
                    <div class="flex gap-1.5 items-center">Interview</div>
                </th>
        </thead>
        <tbody>
            {#each $characters as character}
                <tr>
                    <td class='px-3 py-1'>
                        <div>{character.title}</div>
                    </td>
                    <td class='px-3 py-1'>
                        <div>{formatDate(character.updated_at * 1000)}</div> <!--convert from s to ms-->
                    </td>
                    <td class='px-3 py-1'>
                        <div class='py-1 flex justify-left w-full'>
                            <textarea 
                                class="w-full" 
                                readonly={true}
                                value={character.system_prompt}></textarea>
                            
                        </div>
                    </td>
                    <td class='p-2 px-5 flex justify-left w-full'>
                        <div class="flex">
                            <button 
                                class="px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
                                on:click={() => startInterview(character.character_name, character.system_prompt)}
                            >
                                Start Interview
                            </button>
                        </div>
                        <Tooltip content={'Edit'}>
                            <button
                                class="hover:bg-gray-100 dark:hover:bg-gray-800 transition rounded-lg p-3 ml-3"
                                on:click={() => {
                                    show = true;
                                    selectedCharacter = character
                                }}
                            >
                                <Pencil />
                            </button>
                        </Tooltip>
                        <Tooltip content={'Delete Character'}>
                            <button
                                class="ml-3 p-3 flex self-center w-fit text-sm hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                                on:click={async () => {
                                    deleteChatHandler(character.id);
                                }}
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                    class="w-4 h-4"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                                    />
                                </svg>
                            </button>
                        </Tooltip>
                    </td>

                </tr>
            {/each}
        </tbody>
</div>