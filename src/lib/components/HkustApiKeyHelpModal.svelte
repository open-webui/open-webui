<script lang="ts">
	import {getContext } from 'svelte';

	import Modal from './common/Modal.svelte';
	import Image from './common/Image.svelte';

	const i18n = getContext('i18n');

	export let show = false;

</script>

<Modal bind:show size="lg">
	<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
		<div class="flex justify-between items-start">
			<div class="text-xl font-semibold">
				{$i18n.t('HKUST OPEN API KEY 발급하기')}
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
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">{$i18n.t('Merge Feat')}</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<div class="text-sm dark:text-gray-200">
				10 March 2025
			</div>
		</div>
	</div>

	<div class=" w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class=" overflow-y-scroll max-h-140 scrollbar-hidden">
			<div class="pr-4">
				<div class="font-semibold text-xl mb-1 dark:text-white">
					1. 아래 이미지를 눌러서 HKUST API Developer Portal에 접속합니다.
				</div>
				<a href="https://hkust.developer.azure-api.net/" target="_blank" rel="noopener noreferrer">
				<Image
					src={'assets/images/hkust_api_guide_1.png'}
					imageClassName="rounded-xl object-cover mb-10"
				/>
				</a>
				<div class="font-semibold text-xl mb-1 dark:text-white">
					2. "Azure Active Directory" 버튼을 통해 ITSO 계정으로 HKUST API에 가입합니다.
				</div>
				<Image
					src={'assets/images/hkust_api_guide_2.png'}
					imageClassName=" rounded-xl object-cover mb-10"
				/>
				<div class="font-semibold text-xl mb-1 dark:text-white">
					3. 상단 메뉴에 있는 Products로 이동한 뒤, Azure OpenAI (personal)를 클릭 합니다. <br/>
				</div>
				<Image
					src={'assets/images/hkust_api_guide_3.png'}
					imageClassName=" rounded-xl object-cover mb-10"
				/>
				<div class="font-semibold text-xl mb-1 dark:text-white">
					4. Your subscriptions에 hkust-open-ai를 입력한 뒤 Subscribe 버튼을 클릭합니다.
				</div>
				<Image
					src={'assets/images/hkust_api_guide_4.png'}
					imageClassName=" rounded-xl object-cover mb-10"
				/>
				<div class="font-semibold text-xl mb-1 dark:text-white">
					5. Show를 눌러서 가려진 API key를 확인 한 뒤, 해당 API key를 HKUST Open API Key에 입력합니다.
				</div>
				<Image
					src={'assets/images/hkust_api_guide_5.png'}
					imageClassName=" rounded-xl object-cover mb-10"
				/>
		</div>
		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
				on:click={async () => {
					show = false;
				}}
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			>
				<span class="relative">{$i18n.t("Done")}</span>
			</button>
		</div>
	</div>
</Modal>
