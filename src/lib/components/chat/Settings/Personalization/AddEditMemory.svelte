<script>
	import { createEventDispatcher, getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { addNewMemory, updateMemoryById } from '$lib/apis/memories';
	import { toast } from 'svelte-sonner';
	import SendIcon from '$lib/components/icons/SendIcon.svelte';
	import StopIcon from '$lib/components/icons/StopIcon.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;
	let content = '';

    export let memory = null;
    let updated = false;

    $: {
        if(memory && !updated) {
            content = memory.content;
            updated = true;
        }
    }

	const submitHandler = async () => {
		if(!content) return;
		loading = true;

        let res;

        if(memory) {
            res = await updateMemoryById(localStorage.token, memory.id, content).catch((error) => {
			toast.error(`${error}`);

			return null;
		});
        }else{
            res = await addNewMemory(localStorage.token, content).catch((error) => {
			toast.error(`${error}`);

			return null;
		});
        }

		if (res) {
            if(memory) {
                toast.success($i18n.t('Memory updated successfully'));
            }else{
                toast.success($i18n.t('Memory added successfully'));
            }
			
			content = '';
            updated = false;
            memory = null;
			dispatch('save');
		}

		loading = false;
	};
</script>


	<div>
		<div class="flex flex-col md:flex-row w-full pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="relative">
						<textarea
							bind:value={content}
							class="bg-lightGray-300 text-lightGray-100 placeholder:text-lightGray-100 dark:bg-customGray-900 w-full text-sm resize-none rounded-3xl px-6 pt-6 pb-1 outline-none"
							placeholder={$i18n.t('Enter a detail  about yourself for your LLMs to recall')}
							rows="2"
						/>

						<div class="text-xs font-medium text-lightGray-100/50 dark:text-customGray-100">
							ⓘ {$i18n.t('Refer to yourself as "User" (e.g., "User is learning Spanish")')}
						</div>
						<button
							class="absolute right-6 top-6 text-customGray-900 transition flex flex-row items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if loading}
								<StopIcon className="size-6"/>
							{:else}
								<SendIcon className="size-6"/>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>

