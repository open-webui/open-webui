<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { getContext } from 'svelte';
    
    const i18n = getContext('i18n');
    import { settings } from '$lib/stores';

    import Modal from '$lib/components/common/Modal.svelte';
    import XMark from '$lib/components/icons/XMark.svelte';

    export let show = false;
    export let onSubmit: (password: string) => void;

    let password = '';
    let showPassword = false;

    const submitHandler = () => {
        if (!password || password.trim() === '') {
            toast.error($i18n.t('Please enter a password.'));
            return;
        }

        onSubmit(password);
        show = false;
        password = '';
    };

    $: if (!show) {
        password = '';
        showPassword = false;
    }
</script>

<Modal bind:show size="sm">
    <div class="flex flex-col h-full">
        <div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-1.5">
            <h1 class="text-lg font-medium self-center font-primary">
                {$i18n.t('Enter File Password')}
            </h1>
            <button
                class="self-center"
                aria-label={$i18n.t('Close modal')}
                on:click={() => {
                    show = false;
                }}
            >
                <XMark className="size-5" />
            </button>
        </div>

        <div class="px-5 pb-4">
            <form
                on:submit={(e) => {
                    e.preventDefault();
                    submitHandler();
                }}
            >
                <div class="flex justify-between mb-0.5">
                    <label
                        for="file-password"
                        class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
                    >
                        {$i18n.t('Password')}
                    </label>
                </div>

                <div class="relative">
                    <input
                        id="file-password"
                        class={`w-full pr-10 py-2 px-3 text-sm bg-transparent border dark:border-gray-600 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'} rounded-lg`}
                        type={showPassword ? 'text' : 'password'}
                        bind:value={password}
                        placeholder={$i18n.t('Enter password for encrypted file')}
                        autocomplete="off"
                        required
                    />
                    <button
                        type="button"
                        class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                        on:click={() => (showPassword = !showPassword)}
                        aria-label={showPassword ? $i18n.t('Hide password') : $i18n.t('Show password')}
                    >
                        {#if showPassword}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                class="size-4"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745a10.029 10.029 0 003.3-4.38 1.651 1.651 0 000-1.185A10.004 10.004 0 009.999 3a9.956 9.956 0 00-4.744 1.194L3.28 2.22zM7.752 6.69l1.092 1.092a2.5 2.5 0 013.374 3.373l1.091 1.092a4 4 0 00-5.557-5.557z"
                                    clip-rule="evenodd"
                                />
                                <path
                                    d="M10.748 13.93l2.523 2.523a9.987 9.987 0 01-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 010-1.186A10.007 10.007 0 012.839 6.02L6.07 9.252a4 4 0 004.678 4.678z"
                                />
                            </svg>
                        {:else}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                class="size-4"
                            >
                                <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
                                <path
                                    fill-rule="evenodd"
                                    d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                        {/if}
                    </button>
                </div>

                <div class="flex justify-end gap-2 pt-3 bg-gray-50 dark:bg-gray-900/50">
                    <button
                        class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition rounded-full"
                        type="button"
                        on:click={() => {
                            show = false;
                        }}
                    >
                        {$i18n.t('Cancel')}
                    </button>
                    <button
                        class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full"
                        type="submit"
                    >
                        {$i18n.t('Submit')}
                    </button>
                </div>
            </form>
        </div>
    </div>
</Modal>