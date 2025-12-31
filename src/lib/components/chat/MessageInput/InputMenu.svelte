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
			class="flex flex-col items-start p-5 gap-2 min-w-max bg-gray-200/20 dark:bg-gray-600/30 shadow-lg backdrop-blur-xl rounded-2xl rounded-bl z-50 text-gray-950 dark:text-white text-caption border-0 max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin transition"
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
							class="flex flex-row items-center justify-between p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
							on:click={() => {
								tab = 'proficiency';
							}}
						>
							<div class="flex items-center gap-1">
								<AdjustmentsHorizontal className="size-5" />
								<span>수준</span>
							</div>
							<div class="text-gray-400">
								<ChevronRight />
							</div>
						</button>

						<button
							class="flex flex-row items-center justify-between p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
							on:click={() => {
								tab = 'response_style';
							}}
						>
							<div class="flex items-center gap-1">
								<ChatBubbleOval className="size-5" />
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
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl bg-gray-200/20 dark:bg-gray-600/30 hover:bg-gray-200/30 dark:hover:bg-gray-600/40 transition cursor-pointer text-caption {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								if (fileUploadEnabled) {
									uploadFilesHandler();
								}
							}}
						>
							<FolderOpen className="size-5" />
							<span>파일 첨부</span>
						</DropdownMenu.Item>
					</Tooltip>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								if (fileUploadEnabled) {
									if (!detectMobile()) {
										screenCaptureHandler();
									} else {
										const cameraInputElement = document.getElementById('camera-input');

										if (cameraInputElement) {
											cameraInputElement.click();
										}
									}
								}
							}}
						>
							<Camera className="size-5" />
							<span>{$i18n.t('Capture')}</span>
						</DropdownMenu.Item>
					</Tooltip>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								if (fileUploadEnabled) {
									showAttachWebpageModal = true;
								}
							}}
						>
							<GlobeAlt className="size-5" />
							<span>{$i18n.t('Attach Webpage')}</span>
						</DropdownMenu.Item>
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
								class="flex flex-row items-center justify-between p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption {!fileUploadEnabled
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
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-xs leading-[18px] {!fileUploadEnabled
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
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
								class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption {!fileUploadEnabled
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
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<span>{$i18n.t('Microsoft OneDrive')}</span>
					</button>

					{#if $config?.features?.enable_onedrive_personal}
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption text-left"
							on:click={() => {
								uploadOneDriveHandler('personal');
							}}
						>
							<span>{$i18n.t('Microsoft OneDrive (personal)')}</span>
						</DropdownMenu.Item>
					{/if}

					{#if $config?.features?.enable_onedrive_business}
						<DropdownMenu.Item
							class="flex flex-row items-center p-1 gap-1 w-full h-auto rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption text-left"
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
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
								class="flex flex-row items-center justify-between py-1 px-2 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
						<div class="p-2 text-center text-gray-500 text-caption">옵션이 없습니다</div>
					{/if}
				</div>
			{:else if tab === 'response_style'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full items-center p-1 gap-1 h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
								class="flex flex-row items-center justify-between py-1 px-2 gap-1 w-full h-7 rounded-xl hover:bg-gray-200/20 dark:hover:bg-gray-600/30 transition cursor-pointer text-caption"
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
						<div class="p-2 text-center text-gray-500 text-caption">옵션이 없습니다</div>
					{/if}
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
