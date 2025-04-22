<script>
	import { createEventDispatcher, getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { addNewMemory, updateMemoryById } from '$lib/apis/memories';
	import { toast } from 'svelte-sonner';

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
			console.log(res);
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
		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="">
						<textarea
							bind:value={content}
							class=" dark:bg-customGray-900 w-full text-sm resize-none rounded-3xl p-3"
							rows="2"
							placeholder={$i18n.t('Enter a detail  about yourself for your LLMs to recall')}
						/>

						<div class="text-xs text-gray-500">
							ⓘ {$i18n.t('Refer to yourself as "User" (e.g., "User is learning Spanish")')}
						</div>
					</div>

					<div class="flex justify-end pt-1 text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-3xl flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Add')}

							{#if loading}
								<div class="ml-2 self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
										><style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}
											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style><path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/><path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/></svg
									>
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>

