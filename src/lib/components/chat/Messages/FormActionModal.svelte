<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { DateInput } from 'date-picker-svelte';
	import Textfield from '@smui/textfield';
	import Select, { Option } from '@smui/select';

	const i18n = getContext('i18n');

	export let show = false;
	export let citation;

	let mergedDocuments = [];
	let startDate = new Date();
	let endDate = new Date();
	const minDate = new Date();
	let remark = '';
	let employeeID = '';
	let phone = '';
	let type = '';
	let address = '';
	let dayCount = 0;
	const leaves = ['Annual Leave', 'Sick Leave'];

	$: if (citation) {
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i]
			};
		});
	}
	// $: if (show) {
	// 	let diff = new Date(endDate).getTime() - new Date(startDate).getTime();
	// 	count = diff / 1000 / 60 / 60 / 24;
	// }
	$: dayCount = (new Date(endDate).getTime() - new Date(startDate).getTime()) / 1000 / 60 / 60 / 24;

	const handleConfirm = () => {
		window.alert('submitted');
		const formData = {
			'{NAME}': 'John Doe',
			'{ID}': 'AI40051',
			'{JOBTITLE}': 'NLP Engineer',
			'{DEPT}': 'CIAI Engineering Team',
			'{LEAVETYPE}': type,
			'{REMARKS}': remark,
			'{LEAVEFROM}': startDate,
			'{LEAVETO}': endDate,
			'{DAYS}': dayCount,
			'{ADDRESS}': address,
			'{TELE}': phone,
			'{EMAIL}': 'nikhil.ranjan@mbzuai.ac.ae',
			'{DATE}': new Date()
		};
		console.info(formData, 'dddd');
		show = false;
	};
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center capitalize">
				<!-- {$i18n.t('Citation')} -->
			</div>
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

		<div class="flex flex-col md:flex-row w-full px-6 pb-5 md:space-x-4">
			<div class=" w-full dark:text-gray-200 overflow-y-scroll scrollbar-hidden p-5">
				<!-- Leave Type & ID  -->
				<div class="flex w-full">
					<div class="w-2/3 mr-10">
						<div class="mb-2 text-sm">Type of Leave</div>
						<div class="flex items-center">
							<img src="/icon/type.png" alt="icon-form" class="h-[22px] mr-2" />
							<Select variant="outlined" bind:type class="flex-1">
								{#each leaves as leaveType}
									<Option value={leaveType}>{leaveType}</Option>
								{/each}
							</Select>
						</div>
					</div>
					<div class="w-1/3">
						<div class="mb-2 text-sm">ID #</div>
						<div class="flex items-center">
							<img src="/icon/id.png" alt="icon-form" class="h-[29px] mr-2" />
							<Textfield variant="outlined" bind:value={employeeID} class="w-full" />
						</div>
					</div>
				</div>
				<!-- Start & End Date  -->
				<div class="flex w-full items-center">
					<div class=" mr-10">
						<div class="mt-4 mb-2 text-sm">Leave Applied From/To</div>
						<div class="flex items-center">
							<img src="/icon/calendar.png" alt="icon-form" class="h-[24px] mr-2" />
							<DateInput bind:value={startDate} format="yyyy-MM-dd" min={minDate} class="mr-2" />
							-
							<DateInput
								bind:value={endDate}
								format="yyyy-MM-dd"
								bind:min={startDate}
								class="ml-2"
							/>
						</div>
					</div>
					<div class="">
						<div class="mt-4 text-sm">Leave Days</div>
						<div class="my-2 flex items-center">
							<img src="/icon/calendar1.png" alt="icon-form" class="h-[24px] mr-2" />
							{dayCount} Days
						</div>
					</div>
				</div>
				<!-- Address -->
				<div class="mt-4 mb-2 text-sm">Address while on leave</div>
				<div class="flex items-center">
					<img src="/icon/address.png" alt="icon-form" class="h-[34px] mr-2" />
					<Textfield variant="outlined" bind:value={address} class="w-full" />
				</div>
				<!-- Phone  -->
				<div class="mt-4 mb-2 text-sm">Telephone (Local)</div>
				<div class="flex items-center">
					<img src="/icon/phone.png" alt="icon-form" class="h-[30px] mr-2" />
					<Textfield variant="outlined" bind:value={phone} class="w-1/2" />
				</div>
				<!-- Remark  -->
				<div class="mt-4 mb-2 text-sm">Employee Remarks (Optional)</div>
				<div class="flex w-full">
					<img src="/icon/note.png" alt="icon-form" class="h-[32px] mr-2" />
					<Textfield textarea bind:value={remark} class="flex-1" />
				</div>
				<div class="flex mt-4 justify-end">
					<button
						class="py-1 px-12 rounded-lg border border-black/opacity-3 text-black/opacity-60 text-sm"
						on:click={() => {
							show = false;
						}}>Cancel</button
					>
					<button
						class="py-1 px-12 ml-6 text-white bg-[#1595F4] rounded-lg text-sm"
						on:click={() => {
							handleConfirm();
						}}>Confirm</button
					>
				</div>
			</div>
		</div>
	</div>
</Modal>
