<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateCharityById } from '$lib/apis/charities';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedCharity;

	let _charity = {
		name: '',
		charity_id: '',
		website: '',
		email: ''
	};

	const submitHandler = async () => {
		const res = await updateCharityById(localStorage.token, selectedCharity.id, _charity).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

		if (res) {
			dispatch('save');
			show = false;
		}
	};

	onMount(() => {
		if (selectedCharity) {
			_charity = selectedCharity;
		}
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Edit Charity')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class=" px-5 pt-3 pb-5">
						<div class=" flex flex-col space-y-1.5">
							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="text"
										bind:value={_charity.name}
										placeholder={$i18n.t('Enter Charity Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<hr class=" border-gray-100 dark:border-gray-850 my-2.5 w-full" />
							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Charity ID')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="number"
										bind:value={_charity.charity_id}
										placeholder={$i18n.t('Enter Charity ID')}
										autocomplete="off"
									/>
								</div>
							</div>

							<hr class=" border-gray-100 dark:border-gray-850 my-2.5 w-full" />

							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Charity Website')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="url"
										bind:value={_charity.website}
										placeholder={$i18n.t('Enter Charity Website')}
										autocomplete="off"
									/>
								</div>
							</div>

							<hr class=" border-gray-100 dark:border-gray-850 my-2.5 w-full" />

							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Charity Email')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="email"
										bind:value={_charity.email}
										placeholder={$i18n.t('Enter Charity Email')}
										autocomplete="off"
									/>
								</div>
							</div>

							<hr class=" border-gray-100 dark:border-gray-850 my-2.5 w-full" />
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="submit"
							>
								{$i18n.t('Save')}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}
	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
