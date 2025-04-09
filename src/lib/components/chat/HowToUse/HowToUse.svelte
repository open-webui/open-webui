<script lang="ts">
	import { createEventDispatcher, getContext, tick } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	
	export let selectedModel: string = 'Shrl';
	
	// 탭 상태 관리
	let activeTab = 0;
	
	// 탭 데이터
	const tabs = [
		{ id: 0, title: 'Basic Usage', icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ id: 1, title: 'Model Selection', icon: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z' },
		{ id: 2, title: 'Advanced Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }
	];
	
	// 탭 내용
	const tabContents = [
		{
			title: $i18n?.t('Basic Usage'),
			content: [
				{
					title: $i18n?.t('1. Select a Model'),
					description: $i18n?.t('Choose a suitable model from the model list in the top left corner.')
				},
				{
					title: $i18n?.t('2. Check Question Guide'),
					description: $i18n?.t('You can check what questions you can ask for each model in the "Model Selection" menu in the right tab.')
				},
				{
					title: $i18n?.t('3. Fact-based Answers & Sources'),
					description: $i18n?.t('Answers are provided based on official documents, and you can check the original text through the source link at the bottom.')
				},
                {
					title: $i18n?.t('4. OpenAI Models Available'),
					description: $i18n?.t('In addition to official document-based models, you can also use GPT-4o-mini and GPT-4o models provided by OpenAI.')
				},
                {
					title: $i18n?.t('5. Multiple Model Selection'),
					description: $i18n?.t('You can select multiple models to ask questions simultaneously.')
				},
                {
					title: $i18n?.t('6. Credit Information'),
					description: $i18n?.t('The Credit required for model use is provided by the school through 8 HKD worth of API per month and is reset at the beginning of each month. The official document-based model consumes about 0.005 HKD per question on average.')
				},
                {
					title: $i18n?.t('7. Tips for Better Answers'),
					description: $i18n?.t('While it is proficient in Korean questions, you can get more accurate answers by asking in English.')
				}
			]
		},
		{
			title: $i18n?.t('Model Selection'),
			content: [
				{
					title: $i18n?.t('GPT-4o-mini & GPT-4o'),
					description: $i18n?.t('These are the same models provided by OpenAI.')
				},
				{
					title: $i18n?.t('Student Housing and Residential Life'),
					description: $i18n?.t('This model is based on documents from shrl.hkust.edu.hk. It is suitable for questions about housing (application, hall points, housing regulations, check-in-check-out, shuttle bus, Off-campus, etc.).')
				},
				{
					title: $i18n?.t('Academic Registry Office'),
					description: $i18n?.t('This model is based on documents from registry.hkust.edu.hk. It is suitable for questions about leave of absence, credit regulations, study extension, credit transfer, transcript inquiries, SIS, and other academic support.')
				},
				{
					title: $i18n?.t('Campus Services Office & Dean\'s Office'),
					description: $i18n?.t('This model is based on documents from (cso.hkust.edu.hk, dst.hkust.edu.hk). It is suitable for questions about campus facilities, campus activities, transportation, and other student support.')
				},
				{
					title: $i18n?.t('IT Services Office'),
					description: $i18n?.t('This model is based on documents from (itso.hkust.edu.hk). It is suitable for questions about VPN setup, printer usage, 2FA authentication, and other school IT services.')
				},
				{
					title: $i18n?.t('Undergraduate Research Opportunities Program'),
					description: $i18n?.t('This model is based on documents from urop.hkust.edu.hk. It is suitable for questions about UROP applications, previous project inquiries, and related matters.')
				},
                {
					title: $i18n?.t('Study Abroad'),
					description: $i18n?.t('This model is based on documents from studyabroad.hkust.edu.hk. It is suitable for questions about study abroad applications and related matters.')
				},
			]
		},
		{
			title: $i18n?.t('Advanced Settings'),
			content: [
				{
					title: $i18n?.t('System Prompt'),
					description: $i18n?.t('You can adjust the model\'s behavior and response method using the system prompt.')
				}
			]
		}
	];
</script>

<div class="dark:text-white">
	<div class="flex items-center justify-between dark:text-gray-100 mb-2">
		<div class="text-lg font-medium self-center font-primary">{$i18n?.t('How to use')}</div>
		<button
			class="self-center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-7" />
		</button>
	</div>

    <div class="px-4 py-4 bg-white dark:shadow-lg dark:bg-gray-850 border border-gray-100 dark:border-gray-850 rounded-xl">
        <!-- 탭 네비게이션 -->
        <div class="flex border-b border-gray-200 dark:border-gray-700 mb-4">
            {#each tabs as tab}
                <button
                    class="flex items-center py-2 px-4 text-sm font-medium {activeTab === tab.id ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-400 dark:border-blue-400' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}"
                    on:click={() => activeTab = tab.id}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={tab.icon} />
                    </svg>
                    {tab.title}
                </button>
            {/each}
        </div>

        <!-- 탭 내용 -->
        <div class="space-y-4">
            {#each tabContents[activeTab].content as item}
                <div class="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <h3 class="font-medium mb-2">{item.title}</h3>
                    <p class="text-sm text-gray-600 dark:text-gray-400">{item.description}</p>
                </div>
            {/each}
        </div>
    </div>
</div>
