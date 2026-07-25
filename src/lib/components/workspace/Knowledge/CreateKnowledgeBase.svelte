<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import { Datepicker, type DateOrRange } from "flowbite-svelte";


	import { user } from '$lib/stores';
	import { createNewKnowledge } from '$lib/apis/knowledge';

	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let loading = false;

	let name = '';
	let description = '';
	let registrationNumber = ''
	let accessGrants = [];
	let registrationDate = new Date();

	const onDateSelect = (date: DateOrRange) => {
		registrationDate = date;
	};

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(localStorage.token, {
			name, 
			description, 
			accessGrants, 
			registrationDate, 
			registrationNumber, 
		}).catch(
			(e) => {
				toast.error(`${e}`);
			}
		);

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			goto(`/workspace/knowledge/${res.id}`);
		}

		loading = false;
	};
</script>

<div class="w-full max-h-full">
	<button
		class="flex space-x-1"
		on:click={() => {
			goto('/workspace/knowledge');
		}}
	>
		<div class=" self-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
	</button>

	<form
		class="flex flex-col max-w-lg mx-auto mt-10 mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class=" w-full flex flex-col justify-center">
			<div class=" text-2xl font-medium font-primary mb-2.5">
				{$i18n.t('Create a knowledge base')}
			</div>

			<div class="w-full flex flex-col gap-2.5">
				<div class="w-full">
					<div class=" text-sm mb-2">{$i18n.t('What are you working on?')}</div>

					<div class="w-full mt-1">
						<input
							class="w-full placeholder:text-gray-400 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Name')}
							required
						/>
					</div>
				</div>

				<div>
					<div class="text-sm mb-2">{$i18n.t('Describe what this knowledge base is about, for what purposes....')}</div>

					<div class=" w-full mt-1">
						<textarea
							class="w-full placeholder:text-gray-400 resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							rows="4"
							bind:value={description}
							placeholder={$i18n.t('Put objectives here...')}
						/>
					</div>
				</div>

				<div class="flex gap-3 justify-between">
<div class="mb-6">
					<div class="text-sm mb-2">{$i18n.t('Enter registration identifier')}</div>

					<div class=" w-full mt-1">
						<input
							type="text"
							class="w-full placeholder:text-gray-400 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={registrationNumber}
							placeholder={$i18n.t('registration identifier')}
						/>
					</div>
				</div>
				<div class="md:w-1/2">
					<div class="text-sm mb-2">{$i18n.t('Enter registration date')}</div>
					<Datepicker
						bind:value={registrationDate}
						color="dark"
						placeholder={$i18n.t('Select registration date')}
						firstDayOfWeek={1}
						onselect={onDateSelect}
						availableTo={new Date()}
					/>
				</div>
				</div>

			
			</div>
		</div>

		<div class="mt-2">
			<AccessControl
				bind:accessGrants
				accessRoles={['read', 'write']}
				share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
				sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
				shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
					$user?.role === 'admin'}
			/>
		</div>

		<div class="flex justify-end mt-2">
			<div>
				<button
					class=" text-sm px-4 py-2 transition rounded-lg {loading
						? ' cursor-not-allowed bg-gray-100 dark:bg-gray-800'
						: ' bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'} flex"
					type="submit"
					disabled={loading}
				>
					<div class=" self-center font-medium">{$i18n.t('Create Knowledge')}</div>

					{#if loading}
						<div class="ml-1.5 self-center">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
