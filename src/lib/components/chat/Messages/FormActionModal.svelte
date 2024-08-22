<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { DateInput } from 'date-picker-svelte';
	import Textfield from '@smui/textfield';
	import { createEventDispatcher } from 'svelte';
	import { user } from '$lib/stores';
	import { submitLeaveForm } from '$lib/apis/chats';
	import { toast } from 'svelte-sonner';
	// import Select, { Option } from '@smui/select';

	const i18n = getContext('i18n');

	export let show = false;
	export let citation;

	const dispatch = createEventDispatcher();

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
	let days = 0;
	const leaves = [
		'Annual Leave',
		'Sick Leave',
		'Maternity Leave',
		'Paternity Leave',
		'Unpaid Leave',
		'Compassionate Leave',
		'Administrative Leave',
		'Emergency Leave',
		'Educational Leave',
		'Lecture, Course/Exams',
		'Escort Leave',
		'Military Service',
		'Iddah Leave',
		'Haj Leave'
	];

	$: if (citation) {
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i]
			};
		});
	}
	// $: dayCount = (new Date(endDate).getTime() - new Date(startDate).getTime()) / 1000 / 60 / 60 / 24 + 1;
	$: dayCount = countWeekdays(startDate, endDate);
	$: if (new Date(startDate).getTime() - new Date(endDate).getTime() > 0) {
		endDate = new Date(startDate);
	}
	$: if (dayCount) {
		days = dayCount;
	}

	const countWeekdays = (startDate, endDate) => {
		// 确保日期是正确顺序
		if (endDate < startDate) return 0;

		let count = 0;
		let currentDate = new Date(startDate);

		while (currentDate <= endDate) {
			const dayOfWeek = currentDate.getDay();
			// 跳过周六和周日
			if (dayOfWeek !== 0 && dayOfWeek !== 6) {
				count++;
			}
			// 日期加一天
			currentDate.setDate(currentDate.getDate() + 1);
		}
		return count;
	};

	const dateFormatter = (val) => {
		const date = val ? new Date(val) : new Date();
		// const dateString = date.toDateString().split(' ')
		// dateString.splice(0,1)
		// return `${dateString[1]} ${dateString[0]} ${dateString[2]}`
		const months = [
			'January',
			'February',
			'March',
			'April',
			'May',
			'June',
			'July',
			'August',
			'September',
			'October',
			'November',
			'December'
		];

		const day = date.getDate();
		const month = months[date.getMonth()];
		const year = date.getFullYear();

		// 添加后缀
		let suffix = 'th';
		if (day % 10 === 1 && day !== 11) {
			suffix = 'st';
		} else if (day % 10 === 2 && day !== 12) {
			suffix = 'nd';
		} else if (day % 10 === 3 && day !== 13) {
			suffix = 'rd';
		}

		return `${month} ${day}${suffix}, ${year}`;
	};
	const handleConfirm = () => {
		if (!$user.extra_sso) {
			toast.error('User type error. Only supports users login with outlook account.');
			return;
		}
		const ssoData = JSON.parse($user.extra_sso);
		const formData = {
			name: $user.name,
			employee_id: ssoData.emp_id,
			job_title: ssoData.job_title,
			dept: ssoData.department,
			type_of_leave: type,
			remarks: remark,
			leavefrom: dateFormatter(startDate),
			leaveto: dateFormatter(endDate),
			days: String(days),
			address: address,
			tele: phone,
			email: $user.email,
			date: dateFormatter()
		};
		submitLeaveForm(localStorage.token, formData)
			.then((res) => {
				dispatch('confirm', formData);
				show = false;
			})
			.catch((err) => {
				toast(err.detail + ' Submission failed.');
				return;
			});
	};
</script>

<!-- <Modal size="lg" bind:show> -->
<div class="w-3/4 bg-[#ffffffdd] dark:bg-[#ffffff80] rounded-lg my-4 mx-2 modal-content">
	<!-- <div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center capitalize">
				{$i18n.t('Citation')}
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
		</div> -->

	<div class="flex flex-col md:flex-row w-full px-6 py-5 md:space-x-4">
		<div class=" w-full dark:text-gray-900 overflow-y-scroll scrollbar-hidden p-5">
			<form
				on:submit|preventDefault={() => {
					handleConfirm();
				}}
			>
				<!-- Leave Type & ID  -->
				<div class="flex w-full">
					<div class="w-1/2 mr-16">
						<div class="mb-2 text-sm">Type of Leave</div>
						<div class="flex items-center">
							<img src="/icon/type.png" alt="icon-form" class="h-[22px] mr-2" />
							<select
								required
								bind:value={type}
								class="flex-1 rounded-md px-2 h-[44px] bg-transparent"
								style="border: 1px solid #0000004D"
							>
								{#each leaves as leaveType}
									<option value={leaveType}>{leaveType}</option>
								{/each}
							</select>
						</div>
					</div>
					<!-- <div class="w-1/3">
						<div class="mb-2 text-sm">ID #</div>
						<div class="flex items-center">
							<img src="/icon/id.png" alt="icon-form" class="h-[29px] mr-2" />
							<Textfield required variant="outlined" bind:value={employeeID} class="w-full" />
						</div>
					</div> -->
				</div>
				<!-- Start & End Date  -->
				<div class="flex w-full items-center">
					<div class=" mr-10">
						<div class="mt-4 mb-2 text-sm">Leave Applied From/To</div>
						<div class="flex items-center">
							<img src="/icon/calendar.png" alt="icon-form" class="h-[24px] mr-2" />
							<DateInput
								required
								bind:value={startDate}
								format="yyyy-MM-dd"
								min={minDate}
								class="mr-2"
							/>
							<span>-</span>
							<DateInput
								required
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
							<Textfield required variant="outlined" bind:value={days} class="w-1/2 mr-2" />
							<span>Day(s)</span>
						</div>
					</div>
				</div>
				<!-- Address -->
				<div class="mt-4 mb-2 text-sm">Address while on leave</div>
				<div class="flex items-center">
					<img src="/icon/address.png" alt="icon-form" class="h-[34px] mr-2" />
					<Textfield required variant="outlined" bind:value={address} class="w-full" />
				</div>
				<!-- Phone  -->
				<div class="mt-4 mb-2 text-sm">Telephone (Local)</div>
				<div class="flex items-center">
					<img src="/icon/phone.png" alt="icon-form" class="h-[30px] mr-2" />
					<Textfield required variant="outlined" bind:value={phone} class="w-1/2" />
				</div>
				<!-- Remark  -->
				<div class="mt-4 mb-2 text-sm">Employee Remarks (Optional)</div>
				<div class="flex w-full">
					<img src="/icon/note.png" alt="icon-form" class="h-[32px] mr-2" />
					<Textfield textarea bind:value={remark} class="flex-1" />
				</div>
				<div class="flex mt-4 justify-end">
					<button
						class="py-1 px-12 rounded-lg border border-black/opacity-3 text-black/opacity-60 text-sm dark:text-white"
						on:click={() => {
							// show = false;
							dispatch('cancel');
						}}>Cancel</button
					>
					<button class="py-1 px-12 ml-6 text-white bg-[#1595F4] rounded-lg text-sm" type="submit"
						>Confirm</button
					>
				</div>
			</form>
		</div>
	</div>
</div>

<!-- </Modal> -->

<style>
	.modal-content {
		animation: scaleUp 0.5s ease-out forwards;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.85);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
