<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { config, user, tools as _tools, mobile, knowledge, chats } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getAvailablePersonas } from '$lib/apis/prompt-groups';
	import type { AvailablePersonas, PersonaOption } from '$lib/apis/prompt-groups';

	import { createPicker } from '$lib/utils/google-drive-picker';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Agile from '$lib/components/icons/Agile.svelte';
	import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import Chats from './InputMenu/Chats.svelte';
	import Notes from './InputMenu/Notes.svelte';
	import Knowledge from './InputMenu/Knowledge.svelte';
	import AttachWebpageModal from './AttachWebpageModal.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';

	const i18n = getContext('i18n');

	export let files = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;
	export let inputFilesHandler: Function;

	export let uploadGoogleDriveHandler: Function;
	export let uploadOneDriveHandler: Function;

	export let onUpload: Function;
	export let onClose: Function;

	export let proficiencyLevel = '2';  // 기본값: 중급
	export let responseStyle = 'diagnosis';  // 기본값: 학생 진단 브리핑

	// 동적 페르소나 옵션
	let availablePersonas: AvailablePersonas | null = null;
	let personasLoading = false;

	// 라벨 헬퍼 함수 (프롬프트 title 사용)
	const getPersonaLabel = (option: PersonaOption): string => {
		return option.prompts[0]?.title ?? option.value;
	};

	// 현재 선택된 값의 라벨 가져오기
	const getSelectedProficiencyLabel = (): string => {
		if (!availablePersonas) return proficiencyLevel;
		const found = availablePersonas.proficiency_levels.find(p => p.value === proficiencyLevel);
		return found ? getPersonaLabel(found) : proficiencyLevel;
	};

	const getSelectedStyleLabel = (): string => {
		if (!availablePersonas) return responseStyle;
		const found = availablePersonas.response_styles.find(s => s.value === responseStyle);
		return found ? getPersonaLabel(found) : responseStyle;
	};

	// 페르소나 로드
	const loadPersonas = async () => {
		if (availablePersonas) return; // 이미 로드됨
		personasLoading = true;
		try {
			availablePersonas = await getAvailablePersonas(localStorage.token);
			// 기본값 설정: 첫 번째 옵션으로
			if (availablePersonas.proficiency_levels.length > 0 && !availablePersonas.proficiency_levels.find(p => p.value === proficiencyLevel)) {
				proficiencyLevel = availablePersonas.proficiency_levels[0].value;
			}
			if (availablePersonas.response_styles.length > 0 && !availablePersonas.response_styles.find(s => s.value === responseStyle)) {
				responseStyle = availablePersonas.response_styles[0].value;
			}
		} catch (e) {
			console.error('Failed to load personas:', e);
		}
		personasLoading = false;
	};

	// 컴포넌트 마운트 시 페르소나 로드
	onMount(() => {
		loadPersonas();
	});

	let show = false;
	let tab = '';

	let showAttachWebpageModal = false;

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	$: if (!fileUploadEnabled && files.length > 0) {
		files = [];
	}

	const detectMobile = () => {
		const userAgent = navigator.userAgent || navigator.vendor || window.opera;
		return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
	};

	const handleFileChange = (event) => {
		const inputFiles = Array.from(event.target?.files);
		if (inputFiles && inputFiles.length > 0) {
			console.log(inputFiles);
			inputFilesHandler(inputFiles);
		}
	};

	const init = async () => {
		if ($knowledge === null) {
			await knowledge.set(await getKnowledgeBases(localStorage.token));
		}
	};

	$: if (show) {
		init();
	}

	const onSelect = (item) => {
		if (files.find((f) => f.id === item.id)) {
			return;
		}
		files = [
			...files,
			{
				...item,
				status: 'processed'
			}
		];

		show = false;
	};
</script>

<AttachWebpageModal
	bind:show={showAttachWebpageModal}
	onSubmit={(e) => {
		onUpload(e);
	}}
/>

<!-- Hidden file input used to open the camera on mobile -->
<input
	id="camera-input"
	type="file"
	accept="image/*"
	capture="environment"
	on:change={handleFileChange}
	style="display: none;"
/>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="min-w-30 flex flex-col items-start p-2 gap-3 min-w-max bg-gray-200/20 dark:bg-gray-600/30 shadow-lg backdrop-blur-xl rounded-2xl rounded-bl z-50 text-gray-950 dark:text-white text-body-4 border-0 max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin transition"
			sideOffset={4}
			alignOffset={-6}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					<!-- 학습 설정 섹션 -->
					<div class="w-full pb-2 mb-2 border-b border-gray-200/50 dark:border-gray-200/50">
						<button
							class="flex flex-row items-center justify-between p-6 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
							on:click={() => {
								tab = 'proficiency';
							}}
						>
							<div class="flex items-center gap-1">
								<!-- psychology_alt icon -->
								<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
									<path d="M6.25 18C6.0375 18 5.85938 17.928 5.71563 17.784C5.57188 17.641 5.5 17.462 5.5 17.25V14.354C4.70833 13.688 4.09375 12.885 3.65625 11.946C3.21875 11.008 3 10.019 3 8.979C3 7.041 3.68257 5.393 5.04771 4.036C6.41284 2.679 8.07064 2 10.0208 2C11.5347 2 12.8958 2.406 14.1042 3.219C15.3125 4.031 16.1111 5.09 16.5 6.396L17.875 11.042C17.9444 11.284 17.9062 11.505 17.7604 11.703C17.6146 11.901 17.4167 12 17.1667 12H16V14.5C16 14.913 15.8531 15.266 15.5594 15.559C15.2656 15.853 14.9125 16 14.5 16H12.5V17.25C12.5 17.462 12.4281 17.641 12.2844 17.784C12.1406 17.928 11.9625 18 11.75 18H6.25ZM10 13C10.2361 13 10.4271 12.923 10.5729 12.769C10.7188 12.615 10.7917 12.424 10.7917 12.196C10.7917 11.968 10.7188 11.778 10.5729 11.625C10.4271 11.472 10.2361 11.396 10 11.396C9.76389 11.396 9.57292 11.472 9.42708 11.623C9.28125 11.775 9.20833 11.963 9.20833 12.188C9.20833 12.418 9.28125 12.611 9.42708 12.766C9.57292 12.922 9.76389 13 10 13ZM10.0083 10.458C10.1539 10.458 10.2896 10.403 10.4154 10.292C10.5413 10.181 10.6181 10.042 10.6458 9.875C10.6736 9.681 10.7426 9.501 10.8529 9.338C10.9633 9.173 11.1374 8.985 11.375 8.771C11.6944 8.479 11.9306 8.198 12.0833 7.927C12.2361 7.656 12.3125 7.364 12.3125 7.049C12.3125 6.476 12.0903 5.991 11.6458 5.594C11.2014 5.198 10.6667 5 10.0417 5C9.59722 5 9.19444 5.094 8.83333 5.281C8.47222 5.469 8.19444 5.729 8 6.062C7.90278 6.215 7.88194 6.375 7.9375 6.542C7.99306 6.708 8.09565 6.826 8.24543 6.896C8.39535 6.965 8.54167 6.976 8.68457 6.927C8.82762 6.878 8.95361 6.785 9.0625 6.646C9.1875 6.493 9.33333 6.372 9.5 6.281C9.66667 6.191 9.84572 6.146 10.0371 6.146C10.3381 6.146 10.5876 6.24 10.7858 6.427C10.9842 6.615 11.0833 6.847 11.0833 7.125C11.0833 7.319 11.0312 7.493 10.9271 7.646C10.8229 7.799 10.5694 8.062 10.1667 8.438C9.91667 8.674 9.73611 8.892 9.625 9.094C9.51389 9.295 9.44444 9.549 9.41667 9.854C9.38889 10.007 9.4375 10.146 9.5625 10.271C9.6875 10.396 9.83611 10.458 10.0083 10.458Z" class="fill-gray-500 dark:fill-current"/>
								</svg>
								<span>수준</span>
							</div>
							<div class="text-gray-400">
								<ChevronRight />
							</div>
						</button>

						<button
							class="flex flex-row items-center justify-between p-6 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
							on:click={() => {
								tab = 'response_style';
							}}
						>
							<div class="flex items-center gap-1">
								<!-- sms icon -->
								<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
									<path d="M5 17L3.27333 18.727C3.03556 18.964 2.76389 19.018 2.45833 18.887C2.15278 18.757 2 18.523 2 18.188V5.5C2 5.087 2.14688 4.734 2.44063 4.441C2.73438 4.147 3.0875 4 3.5 4H16.5C16.9125 4 17.2656 4.147 17.5594 4.441C17.8531 4.734 18 5.087 18 5.5V15.5C18 15.913 17.8531 16.266 17.5594 16.559C17.2656 16.853 16.9125 17 16.5 17H5ZM6.7456 11.25C6.9569 11.25 7.1354 11.179 7.2812 11.036C7.4271 10.893 7.5 10.716 7.5 10.504C7.5 10.293 7.4285 10.115 7.2856 9.969C7.1427 9.823 6.9656 9.75 6.7544 9.75C6.5431 9.75 6.3646 9.821 6.2188 9.964C6.0729 10.107 6 10.284 6 10.496C6 10.707 6.0715 10.885 6.2144 11.031C6.3573 11.177 6.5344 11.25 6.7456 11.25ZM9.9956 11.25C10.2069 11.25 10.3854 11.179 10.5312 11.036C10.6771 10.893 10.75 10.716 10.75 10.504C10.75 10.293 10.6785 10.115 10.5356 9.969C10.3927 9.823 10.2156 9.75 10.0044 9.75C9.7931 9.75 9.6146 9.821 9.4688 9.964C9.3229 10.107 9.25 10.284 9.25 10.496C9.25 10.707 9.3215 10.885 9.4644 11.031C9.6073 11.177 9.7844 11.25 9.9956 11.25ZM13.2456 11.25C13.4569 11.25 13.6354 11.179 13.7812 11.036C13.9271 10.893 14 10.716 14 10.504C14 10.293 13.9285 10.115 13.7856 9.969C13.6427 9.823 13.4656 9.75 13.2544 9.75C13.0431 9.75 12.8646 9.821 12.7188 9.964C12.5729 10.107 12.5 10.284 12.5 10.496C12.5 10.707 12.5715 10.885 12.7144 11.031C12.8573 11.177 13.0344 11.25 13.2456 11.25Z" class="fill-gray-500 dark:fill-current"/>
								</svg>
								<span>응답 스타일</span>
							</div>
							<div class="text-gray-400">
								<ChevronRight />
							</div>
						</button>
					</div>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex flex-row items-center justify-between p-6 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4 {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								if (fileUploadEnabled) {
									tab = 'file_attach';
								}
							}}
						>
							<div class="flex items-center gap-1">
								<!-- folder_copy icon -->
								<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
									<path d="M2.5 21C2.0972 21 1.7465 20.851 1.4479 20.552C1.1493 20.253 1 19.903 1 19.5V10.25C1 10.037 1.0715 9.859 1.2144 9.716C1.3573 9.572 1.5344 9.5 1.7456 9.5C1.9569 9.5 2.1354 9.572 2.2812 9.716C2.4271 9.859 2.5 10.037 2.5 10.25V19.5H15.25C15.4625 19.5 15.6406 19.571 15.7844 19.714C15.9281 19.857 16 20.034 16 20.246C16 20.457 15.9281 20.635 15.7844 20.781C15.6406 20.927 15.4625 21 15.25 21H2.5ZM5.5 18C5.0972 18 4.7465 17.851 4.4479 17.552C4.1493 17.253 4 16.903 4 16.5V7.5C4 7.087 4.1493 6.734 4.4479 6.441C4.7465 6.147 5.0972 6 5.5 6H8.3958C8.5933 6 8.7816 6.035 8.9606 6.104C9.1397 6.174 9.3056 6.285 9.4583 6.438L11.0208 8H16.5C16.9125 8 17.2656 8.147 17.5594 8.441C17.8531 8.734 18 9.088 18 9.5V16.5C18 16.903 17.8531 17.253 17.5594 17.552C17.2656 17.851 16.9125 18 16.5 18H5.5Z" class="fill-gray-500 dark:fill-current"/>
								</svg>
								<span>파일 첨부</span>
							</div>
							<div class="text-gray-400">
								<ChevronRight />
							</div>
						</button>
					</Tooltip>

					{#if $config?.features?.enable_notes ?? false}
						<Tooltip
							content={fileUploadCapableModels.length !== selectedModels.length
								? $i18n.t('Model(s) do not support file upload')
								: !fileUploadEnabled
									? $i18n.t('You do not have permission to upload files.')
									: ''}
							className="w-full"
						>
							<button
								class="flex flex-row items-center justify-between p-6 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4 {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'notes';
								}}
							>
								<div class="flex items-center gap-1">
									<PageEdit className="size-5" />
									<span>{$i18n.t('Attach Notes')}</span>
								</div>
								<div class="text-gray-400">
									<ChevronRight />
								</div>
							</button>
						</Tooltip>
					{/if}

					<!-- {#if ($knowledge ?? []).length > 0}
						<Tooltip
							content={fileUploadCapableModels.length !== selectedModels.length
								? $i18n.t('Model(s) do not support file upload')
								: !fileUploadEnabled
									? $i18n.t('You do not have permission to upload files.')
									: ''}
							className="w-full"
						>
							<button
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-sm leading-[20px] {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'knowledge';
								}}
							>
								<Database />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Attach Knowledge')}
									</div>

									<div class="text-gray-400">
										<ChevronRight />
									</div>
								</div>
							</button>
						</Tooltip>
					{/if} -->

					<!-- {#if ($chats ?? []).length > 0}
						<Tooltip
							content={fileUploadCapableModels.length !== selectedModels.length
								? $i18n.t('Model(s) do not support file upload')
								: !fileUploadEnabled
									? $i18n.t('You do not have permission to upload files.')
									: ''}
							className="w-full"
						>
							<button
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-xs leading-[18px] {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'chats';
								}}
							>
								<ClockRotateRight />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Reference Chats')}
									</div>

									<div class="text-gray-400">
										<ChevronRight />
									</div>
								</div>
							</button>
						</Tooltip>
					{/if} -->

					{#if fileUploadEnabled}
						{#if $config?.features?.enable_google_drive_integration}
							<DropdownMenu.Item
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
								on:click={() => {
									uploadGoogleDriveHandler();
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" class="size-5">
									<path
										d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
										fill="#0066da"
									/>
									<path
										d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
										fill="#00ac47"
									/>
									<path
										d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
										fill="#ea4335"
									/>
									<path
										d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
										fill="#00832d"
									/>
									<path
										d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
										fill="#2684fc"
									/>
									<path
										d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
										fill="#ffba00"
									/>
								</svg>
								<div class="line-clamp-1">{$i18n.t('Google Drive')}</div>
							</DropdownMenu.Item>
						{/if}

						{#if $config?.features?.enable_onedrive_integration && ($config?.features?.enable_onedrive_personal || $config?.features?.enable_onedrive_business)}
							<button
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4 {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'microsoft_onedrive';
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 32 32"
									class="size-5"
									fill="none"
								>
									<mask
										id="mask0_87_7796"
										style="mask-type:alpha"
										maskUnits="userSpaceOnUse"
										x="0"
										y="6"
										width="32"
										height="20"
									>
										<path
											d="M7.82979 26C3.50549 26 0 22.5675 0 18.3333C0 14.1921 3.35322 10.8179 7.54613 10.6716C9.27535 7.87166 12.4144 6 16 6C20.6308 6 24.5169 9.12183 25.5829 13.3335C29.1316 13.3603 32 16.1855 32 19.6667C32 23.0527 29 26 25.8723 25.9914L7.82979 26Z"
											fill="#C4C4C4"
										/>
									</mask>
									<g mask="url(#mask0_87_7796)">
										<path
											d="M7.83017 26.0001C5.37824 26.0001 3.18957 24.8966 1.75391 23.1691L18.0429 16.3335L30.7089 23.4647C29.5926 24.9211 27.9066 26.0001 26.0004 25.9915C23.1254 26.0001 12.0629 26.0001 7.83017 26.0001Z"
											fill="url(#paint0_linear_87_7796)"
										/>
										<path
											d="M25.5785 13.3149L18.043 16.3334L30.709 23.4647C31.5199 22.4065 32.0004 21.0916 32.0004 19.6669C32.0004 16.1857 29.1321 13.3605 25.5833 13.3337C25.5817 13.3274 25.5801 13.3212 25.5785 13.3149Z"
											fill="url(#paint1_linear_87_7796)"
										/>
										<path
											d="M7.06445 10.7028L18.0423 16.3333L25.5779 13.3148C24.5051 9.11261 20.6237 6 15.9997 6C12.4141 6 9.27508 7.87166 7.54586 10.6716C7.3841 10.6773 7.22358 10.6877 7.06445 10.7028Z"
											fill="url(#paint2_linear_87_7796)"
										/>
										<path
											d="M1.7535 23.1687L18.0425 16.3331L7.06471 10.7026C3.09947 11.0792 0 14.3517 0 18.3331C0 20.1665 0.657197 21.8495 1.7535 23.1687Z"
											fill="url(#paint3_linear_87_7796)"
										/>
									</g>
									<defs>
										<linearGradient
											id="paint0_linear_87_7796"
											x1="4.42591"
											y1="24.6668"
											x2="27.2309"
											y2="23.2764"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#2086B8" />
											<stop offset="1" stop-color="#46D3F6" />
										</linearGradient>
										<linearGradient
											id="paint1_linear_87_7796"
											x1="23.8302"
											y1="19.6668"
											x2="30.2108"
											y2="15.2082"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#1694DB" />
											<stop offset="1" stop-color="#62C3FE" />
										</linearGradient>
										<linearGradient
											id="paint2_linear_87_7796"
											x1="8.51037"
											y1="7.33333"
											x2="23.3335"
											y2="15.9348"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#0D3D78" />
											<stop offset="1" stop-color="#063B83" />
										</linearGradient>
										<linearGradient
											id="paint3_linear_87_7796"
											x1="-0.340429"
											y1="19.9998"
											x2="14.5634"
											y2="14.4649"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#16589B" />
											<stop offset="1" stop-color="#1464B7" />
										</linearGradient>
									</defs>
								</svg>

								<div class="flex items-center w-full justify-between">
									<span>{$i18n.t('Microsoft OneDrive')}</span>
									<div class="text-gray-400">
										<ChevronRight />
									</div>
								</div>
							</button>
						{/if}
					{/if}
				</div>
			{:else if tab === 'knowledge'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>{$i18n.t('Knowledge')}</span>
					</button>

					<Knowledge {onSelect} />
				</div>
			{:else if tab === 'notes'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>{$i18n.t('Notes')}</span>
					</button>

					<Notes {onSelect} />
				</div>
			{:else if tab === 'chats'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>{$i18n.t('Chats')}</span>
					</button>

					<Chats {onSelect} />
				</div>
			{:else if tab === 'microsoft_onedrive'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>{$i18n.t('Microsoft OneDrive')}</span>
					</button>

					{#if $config?.features?.enable_onedrive_personal}
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4 text-left"
							on:click={() => {
								uploadOneDriveHandler('personal');
							}}
						>
							<span>{$i18n.t('Microsoft OneDrive (personal)')}</span>
						</DropdownMenu.Item>
					{/if}

					{#if $config?.features?.enable_onedrive_business}
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-auto rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4 text-left"
							on:click={() => {
								uploadOneDriveHandler('organizations');
							}}
						>
							<div class="flex flex-col">
								<span>{$i18n.t('Microsoft OneDrive (work/school)')}</span>
								<span class="text-gray-400">{$i18n.t('Includes SharePoint')}</span>
							</div>
						</DropdownMenu.Item>
					{/if}
				</div>
			{:else if tab === 'proficiency'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>수준 선택</span>
					</button>

					{#if personasLoading}
						<div class="p-2 text-center text-gray-500">로딩 중...</div>
					{:else if availablePersonas && availablePersonas.proficiency_levels.length > 0}
						{#each availablePersonas.proficiency_levels as option}
							<button
								class="flex flex-row items-center justify-between py-3 px-4 gap-1 w-full m-2 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
								on:click={() => {
									proficiencyLevel = option.value;
									tab = '';
								}}
							>
								<span>{getPersonaLabel(option)}</span>
								{#if proficiencyLevel === option.value}
									<Check className="size-5 text-primary-700" />
								{/if}
							</button>
						{/each}
					{:else}
						<div class="p-2 text-center text-gray-500 text-body-4">옵션이 없습니다</div>
					{/if}
				</div>
			{:else if tab === 'response_style'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>응답 스타일 선택</span>
					</button>

					{#if personasLoading}
						<div class="p-2 text-center text-gray-500">로딩 중...</div>
					{:else if availablePersonas && availablePersonas.response_styles.length > 0}
						{#each availablePersonas.response_styles as option}
							<button
								class="flex flex-row items-center justify-between py-3 px-4 gap-1 w-full m-2 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
								on:click={() => {
									responseStyle = option.value;
									tab = '';
								}}
							>
								<span>{getPersonaLabel(option)}</span>
								{#if responseStyle === option.value}
									<Check className="size-5 text-primary-700" />
								{/if}
							</button>
						{/each}
					{:else}
						<div class="p-2 text-center text-gray-500 text-body-4">옵션이 없습니다</div>
					{/if}
				</div>
			{:else if tab === 'file_attach'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center py-3 px-4 gap-1 w-full m-2 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>파일 첨부</span>
					</button>

					<!-- PDF 버튼 -->
					<DropdownMenu.Item
						class="flex flex-row items-center py-3 px-4 gap-1 w-full m-2 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							uploadFilesHandler();
						}}
					>
						<!-- picture_as_pdf icon -->
						<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M8.5 9H9C9.2833 9 9.5208 8.9042 9.7125 8.7125C9.9042 8.5208 10 8.2833 10 8V7.5C10 7.2167 9.9042 6.9792 9.7125 6.7875C9.5208 6.5958 9.2833 6.5 9 6.5H8C7.8667 6.5 7.75 6.55 7.65 6.65C7.55 6.75 7.5 6.8667 7.5 7V10C7.5 10.1333 7.55 10.25 7.65 10.35C7.75 10.45 7.8667 10.5 8 10.5C8.1333 10.5 8.25 10.45 8.35 10.35C8.45 10.25 8.5 10.1333 8.5 10V9ZM8.5 8V7.5H9V8H8.5ZM12 10.5C12.2833 10.5 12.5208 10.4042 12.7125 10.2125C12.9042 10.0208 13 9.7833 13 9.5V7.5C13 7.2167 12.9042 6.9792 12.7125 6.7875C12.5208 6.5958 12.2833 6.5 12 6.5H11C10.8667 6.5 10.75 6.55 10.65 6.65C10.55 6.75 10.5 6.8667 10.5 7V10C10.5 10.1333 10.55 10.25 10.65 10.35C10.75 10.45 10.8667 10.5 11 10.5H12ZM11.5 9.5V7.5H12V9.5H11.5ZM14.5 9H15.006C15.1409 9 15.2569 8.95 15.3542 8.85C15.4514 8.75 15.5 8.6333 15.5 8.5C15.5 8.3667 15.45 8.25 15.35 8.15C15.25 8.05 15.1333 8 15 8H14.5V7.5H15.006C15.1409 7.5 15.2569 7.45 15.3542 7.35C15.4514 7.25 15.5 7.1333 15.5 7C15.5 6.8667 15.4497 6.75 15.3492 6.65C15.2487 6.55 15.1315 6.5 14.9975 6.5H13.9927C13.8587 6.5 13.7431 6.55 13.6458 6.65C13.5486 6.75 13.5 6.8667 13.5 7V10C13.5 10.1333 13.55 10.25 13.65 10.35C13.75 10.45 13.8667 10.5 14 10.5C14.1333 10.5 14.25 10.45 14.35 10.35C14.45 10.25 14.5 10.1333 14.5 10V9ZM6.5 15C6.0875 15 5.73438 14.8531 5.44062 14.5594C5.14687 14.2656 5 13.9125 5 13.5V3.5C5 3.0875 5.14687 2.73438 5.44062 2.44063C5.73438 2.14688 6.0875 2 6.5 2H16.5C16.9125 2 17.2656 2.14688 17.5594 2.44063C17.8531 2.73438 18 3.0875 18 3.5V13.5C18 13.9125 17.8531 14.2656 17.5594 14.5594C17.2656 14.8531 16.9125 15 16.5 15H6.5ZM3.5 18C3.0875 18 2.73438 17.8531 2.44063 17.5594C2.14688 17.2656 2 16.9125 2 16.5V5.75C2 5.5375 2.07146 5.35937 2.21438 5.21562C2.35729 5.07187 2.53437 5 2.74562 5C2.95687 5 3.13542 5.07187 3.28125 5.21562C3.42708 5.35937 3.5 5.5375 3.5 5.75V16.5H14.25C14.4625 16.5 14.6406 16.5715 14.7844 16.7144C14.9281 16.8573 15 17.0344 15 17.2456C15 17.4569 14.9281 17.6354 14.7844 17.7812C14.6406 17.9271 14.4625 18 14.25 18H3.5Z" class="fill-gray-500 dark:fill-current"/>
						</svg>
						<span>PDF</span>
					</DropdownMenu.Item>

					<!-- 캡처 버튼 -->
					<DropdownMenu.Item
						class="flex flex-row items-center py-3 px-4 gap-1 w-full m-2  h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							if (!detectMobile()) {
								screenCaptureHandler();
							} else {
								const cameraInputElement = document.getElementById('camera-input');
								if (cameraInputElement) {
									cameraInputElement.click();
								}
							}
						}}
					>
						<!-- markdown_paste/capture icon -->
						<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M11.2544 17C11.0431 17 10.8646 16.9281 10.7188 16.7844C10.5729 16.6406 10.5 16.4625 10.5 16.25V12C10.5 11.725 10.5979 11.4896 10.7937 11.2938C10.9896 11.0979 11.225 11 11.5 11H16C16.275 11 16.5104 11.0979 16.7063 11.2938C16.9021 11.4896 17 11.725 17 12V16.25C17 16.4625 16.9285 16.6406 16.7856 16.7844C16.6427 16.9281 16.4656 17 16.2544 17C16.0431 17 15.8646 16.9281 15.7188 16.7844C15.5729 16.6406 15.5 16.4625 15.5 16.25V12.5H14.5V14.75C14.5 14.9625 14.4285 15.1406 14.2856 15.2844C14.1427 15.4281 13.9656 15.5 13.7544 15.5C13.5431 15.5 13.3646 15.4281 13.2188 15.2844C13.0729 15.1406 13 14.9625 13 14.75V12.5H12V16.25C12 16.4625 11.9285 16.6406 11.7856 16.7844C11.6427 16.9281 11.4656 17 11.2544 17ZM4.5 17C4.0875 17 3.73437 16.8531 3.44062 16.5594C3.14687 16.2656 3 15.9125 3 15.5V4.5C3 4.0875 3.14687 3.73437 3.44062 3.44062C3.73437 3.14687 4.0875 3 4.5 3H8.0625C8.1736 2.5694 8.4063 2.2118 8.7604 1.9271C9.1146 1.6424 9.5278 1.5 10 1.5C10.4722 1.5 10.8854 1.6424 11.2396 1.9271C11.5938 2.2118 11.8264 2.5694 11.9375 3H15.5C15.9125 3 16.2656 3.14687 16.5594 3.44062C16.8531 3.73437 17 4.0875 17 4.5V8.75C17 8.9625 16.9285 9.1406 16.7856 9.2844C16.6427 9.4281 16.4656 9.5 16.2544 9.5C16.0431 9.5 15.8646 9.4281 15.7188 9.2844C15.5729 9.1406 15.5 8.9625 15.5 8.75V4.5H14V6.25C14 6.4625 13.9281 6.6406 13.7844 6.7844C13.6406 6.9281 13.4625 7 13.25 7H6.75C6.5375 7 6.3594 6.9281 6.2156 6.7844C6.0719 6.6406 6 6.4625 6 6.25V4.5H4.5V15.5H8.25C8.4625 15.5 8.6406 15.5715 8.7844 15.7144C8.9281 15.8573 9 16.0344 9 16.2456C9 16.4569 8.9281 16.6354 8.7844 16.7812C8.6406 16.9271 8.4625 17 8.25 17H4.5ZM9.9956 4.5C10.2069 4.5 10.3854 4.4285 10.5312 4.2856C10.6771 4.1427 10.75 3.9656 10.75 3.7544C10.75 3.5431 10.6785 3.3646 10.5356 3.2188C10.3927 3.0729 10.2156 3 10.0044 3C9.7931 3 9.6146 3.0715 9.4688 3.2144C9.3229 3.3573 9.25 3.5344 9.25 3.7456C9.25 3.9569 9.3215 4.1354 9.4644 4.2812C9.6073 4.4271 9.7844 4.5 9.9956 4.5Z" class="fill-gray-500 dark:fill-current"/>
						</svg>
						<span>캡처</span>
					</DropdownMenu.Item>

					<!-- 링크 버튼 -->
					<!-- <DropdownMenu.Item
						class="flex flex-row items-center py-3 px-4 gap-1 w-full m-2 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-body-4"
						on:click={() => {
							showAttachWebpageModal = true;
						}}
					>
					
						<svg class="size-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M14.5 13.5C14.5 14.748 14.062 15.81 13.186 16.686C12.3101 17.562 11.2481 18 10 18C8.7361 18 7.6701 17.545 6.8021 16.635C5.93403 15.726 5.5 14.632 5.5 13.354V5.25C5.5 4.347 5.81597 3.58 6.4479 2.948C7.0799 2.316 7.8472 2 8.75 2C9.6667 2 10.4375 2.333 11.0625 3C11.6875 3.667 12 4.465 12 5.396V13C12 13.558 11.806 14.03 11.4181 14.418C11.0303 14.806 10.5576 15 10 15C9.4306 15 8.9549 14.798 8.5729 14.394C8.191 13.99 8 13.498 8 12.917V5.75C8 5.537 8.0715 5.359 8.2144 5.216C8.3573 5.072 8.5344 5 8.7456 5C8.9569 5 9.1354 5.072 9.2812 5.216C9.4271 5.359 9.5 5.537 9.5 5.75V13C9.5 13.144 9.5472 13.264 9.6417 13.358C9.7361 13.453 9.8556 13.5 10 13.5C10.1444 13.5 10.2639 13.453 10.3583 13.358C10.4528 13.264 10.5 13.144 10.5 13V5.25C10.5 4.764 10.3299 4.351 9.9896 4.01C9.6493 3.67 9.2347 3.5 8.7458 3.5C8.2571 3.5 7.8439 3.677 7.5062 4.031C7.1687 4.385 7 4.806 7 5.292V13.5C7 14.333 7.2917 15.038 7.875 15.615C8.4583 16.191 9.1667 16.486 10 16.5C10.8333 16.514 11.5417 16.215 12.125 15.604C12.7083 14.993 13 14.257 13 13.396V5.75C13 5.537 13.0715 5.359 13.2144 5.216C13.3573 5.072 13.5344 5 13.7456 5C13.9569 5 14.1354 5.072 14.2812 5.216C14.4271 5.359 14.5 5.537 14.5 5.75V13.5Z" class="fill-gray-500 dark:fill-current"/>
						</svg>
						<span>링크</span>
					</DropdownMenu.Item> -->
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
