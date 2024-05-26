<script lang="ts">
    import Modal from "$lib/components/common/Modal.svelte";
    import { createEventDispatcher, getContext } from 'svelte';
    const dispatch = createEventDispatcher();

    const i18n = getContext('i18n');

    import DefaultParams from "$lib/components/chat/Settings/DefaultParams/DefaultParams.svelte";

    export let show = true
    export let config = {}
    export let onUpdate: Function

    let showParams = true
</script>

<Modal bind:show>
    <div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
        <div class=" text-lg font-medium self-center">{$i18n.t('Settings')}</div>
        <button
                class="self-center"
                on:click={() => {
					show = false;
				}}
        >
            <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="w-5 h-5"
            >
                <path
                        d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                />
            </svg>
        </button>
    </div>

    <div class="flex flex-col h-full justify-between text-sm p-5 md:space-x-4">
        <div class="  pr-1.5 overflow-y-scroll max-h-[25rem]">
            <div>
                <div class=" my-2.5 text-sm font-medium">{$i18n.t('System Prompt')}</div>
                <textarea
                        bind:value={config.system}
                        class="w-full rounded-lg p-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
                        rows="4"
                />
            </div>

<!--            <div>-->
<!--                <div class=" my-2.5 text-sm font-medium">{$i18n.t('User Prompt Template')}</div>-->
<!--                <textarea-->
<!--                        bind:value={userPromptTemplate}-->
<!--                        class="w-full rounded-lg p-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"-->
<!--                        rows="4"-->
<!--                />-->
<!--            </div>-->

            <DefaultParams bind:options={config.model_params} bind:showParams title={$i18n.t('Model Parameters')} />
        </div>

        <div class="flex justify-end pt-3 text-sm font-medium">
            <button
                    class="  px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
                    on:click={() => {
                      onUpdate?.(config)
                      show = false
                    }}
            >
                {$i18n.t('Save')}
            </button>
        </div>
    </div>
</Modal>