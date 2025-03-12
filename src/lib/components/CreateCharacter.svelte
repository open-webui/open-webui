<script lang="ts">
import { generateChatCompletion } from '$lib/apis/ollama';
import { chatCompletion } from '$lib/apis/openai';
import {
	WEBUI_BASE_URL
} from '$lib/constants';
import { splitStream } from '$lib/utils';
import ResponseMessage from './chat/Messages/ResponseMessage.svelte';


let messageEditTextAreaElement: HTMLTextAreaElement;
let editedContent = '';
let stopResponseFlag = false;
let messages = {
    content: ''
}
const systemPrompt = {
    role: 'system',
	content: 'hello'
}
const stopResponse = () => {
    stopResponseFlag = true;
    console.log('stopResponse');
};

const saveCharacter = () => {
    
}

const submitMessage = async () => {
    const [res, controller] = await chatCompletion(
        localStorage.token,
        {
            model: 'llama3.2:latest',
            stream: true,
            messages: [
                systemPrompt,
                {
                    role: 'user',
                    content: editedContent
                }
            ].filter((message) => message)
        },
        `${WEBUI_BASE_URL}/api`
	);
    
    if (res && res.ok) {
        const reader = res.body
            .pipeThrough(new TextDecoderStream())
            .pipeThrough(splitStream('\n'))
            .getReader();

        while (true) {
            const { value, done } = await reader.read();
            if (done || stopResponseFlag) {
                if (stopResponseFlag) {
                    controller.abort('User: Stop Response');
                }
                break;
            }

            try {
                let lines = value.split('\n');

                for (const line of lines) {
                    if (line !== '') {
                        console.log(line);
                        if (line === 'data: [DONE]') {
                            // responseMessage.done = true;
                            messages = messages;
                            console.log('done')
                        } else {
                            let data = JSON.parse(line.replace(/^data: /, ''));

                            // TODO: Langfuse
                            messages.content += data.choices[0].delta.content ?? '';
                            // console.log(data);

                            // if (responseMessage.content == '' && data.choices[0].delta.content == '\n') {
                            //     continue;
                            // } else {
                            //     textareaElement.style.height = textareaElement.scrollHeight + 'px';

                            //     responseMessage.content += data.choices[0].delta.content ?? '';
                            //     messages = messages;

                            //     textareaElement.style.height = textareaElement.scrollHeight + 'px';

                            //     await tick();
                            // }
                        }
                    }
                }
            } catch (error) {
                console.log(error);
            }
        }
    }

}

</script>


<div class="gap-1 my-1.5 pb-1 px-[18px] flex-1 max-h-full overflow-y-auto">
    <div class="text-xl font-medium px-0.5">
        <h1>Create a Character</h1>
        <div class="flex self-center w-[1px] h-6 m-x2.5 bg-gray-50 dark:bg-gray-850"/>
        <div class="text-lg font-medium text-gray-500 dark:text-gray-300">
            {"Paste your character sheet"}
        </div>
    </div>

    <div class=" w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 mb-2">
        <div class="max-h-96 overflow-auto">
            <textarea
                id="message-edit"
                bind:this={messageEditTextAreaElement}
                class=" bg-transparent outline-hidden w-full resize-none"
                bind:value={editedContent}
                on:input={(e) => {
                    // e.target.style.height = '';
                    // e.target.style.height = `${e.target.scrollHeight}px`;
                }}
                on:keydown={(e) => {
                    if (e.key === 'Escape') {
                        document.getElementById('close-edit-message-button')?.click();
                    }

                    const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
                    const isEnterPressed = e.key === 'Enter';

                    if (isCmdOrCtrlPressed && isEnterPressed) {
                        document.getElementById('confirm-edit-message-button')?.click();
                    }
                }}
            />
        </div>

        <div class=" mt-2 mb-1 flex justify-between text-sm font-medium">
            <div>
                <!-- <button
                    id="save-edit-message-button"
                    class=" px-4 py-2 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
                    on:click={() => {
                        // editMessageConfirmHandler(false);
                    }}
                >
                    {'Save'}
                </button> -->
            </div>

            <div class="flex space-x-1.5">
                <button
                    id="close-edit-message-button"
                    class="px-4 py-2 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
                    on:click={() => {
                        stopResponse();
                    }}
                >
                    {'Cancel'}
                </button>

                <button
                    id="confirm-edit-message-button"
                    class="px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
                    on:click={() => {
                        submitMessage();
                    }}
                >
                    {'Send'}
                </button>
            </div>
        </div>
    </div>


    {#if messages.content.length > 0}
        <!-- <ResponseMessage
            {chatId}
            {messages}
        /> -->
        <div>{messages.content}</div>

        <button
            id="confirm-edit-message-button"
            class="px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
            on:click={() => {
                saveCharacter();
            }}
        >
            {'Save Character'}
        </button>
            
    {/if}
</div>


