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
		{ id: 0, title: '기본 사용법', icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ id: 1, title: '모델 선택', icon: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z' },
		{ id: 2, title: '고급 설정', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }
	];
	
	// 탭 내용
	const tabContents = [
		{
			title: '기본 사용법',
			content: [
				{
					title: '1. 모델 선택하기',
					description: '좌측 상단의 모델 리스트에서 질문에 맞는 모델을 선택해보세요.'
				},
				{
					title: '2. 질문 가이드 확인하기',
					description: '각 모델에 어떤 질문을 할 수 있는지는 우측 탭의 "모델 선택" 메뉴에서 확인할 수 있어요.'
				},
				{
					title: '3. 사실 기반 답변 & 출처 제공',
					description: '답변은 공식 문서를 바탕으로 제공되며, 하단의 출처 링크를 통해 원문도 직접 확인할 수 있어요.'
				},
                {
					title: '4. OpenAI 모델도 사용 가능',
					description: '공식 문서 기반 모델 외에도 Open AI에서 제공하는 GPT-4o-mini, GPT-4o 모델도 사용할 수 있어요.'
				},
                {
					title: '5. 복수 모델 선택 가능',
					description: '여러 모델을 동시에 선택하여 질문할 수 있습니다.'
				},
                {
					title: '6. 크레딧 안내',
					description: '모델 사용에 필요한 Credit은 학교에서 매달 8 HKD 상당의 API를 통해 제공되며, 매월 초기화돼요. 공식 문서 기반 모델은 질문 1회당 평균 0.005 HKD 정도가 소모됩니다.'
				},
                {
					title: '7. 더 좋은 답변을 위한 팁',
					description: '한국어 질문에도 능숙하지만, 영어로 질문을 주시면 더 정확한 답변을 얻으실 수 있어요.'
				}
			]
		},
		{
			title: '모델 선택',
			content: [
				{
					title: 'GPT-4o-mini & GPT-4o',
					description: 'Open AI에서 제공하는 모델과 동일합니다.'
				},
				{
					title: '기숙사 (Student Housing and Residential Life)',
					description: '해당 모델은 shrl.hkust.edu.hk의 문서를 기반으로 답변합니다. 기숙사 (신청, 홀포인트, 기숙사 규정, 체크인-체크아웃, 셔틀 버스, Off-campus 등) 관련 질문에 적합합니다.'
				},
				{
					title: '학사지원 (Academic Registry Office)',
					description: '해당 모델은 registry.hkust.edu.hk의 문서를 기반으로 답변합니다. 휴학 신청, 학점 규정, 학업 연장, 크래딧 트랜스퍼, 성적표 조회, SIS 등 학사 지원 관련 질문에 적합합니다.'
				},
				{
					title: '학생지원 (Campus Services Office & Dean\'s Office)',
					description: '해당 모델은 (cso.hkust.edu.hk, dst.hkust.edu.hk)의 문서를 기반으로 답변합니다. 학교 시설, 교내 활동, 교통수단 등 학생 지원 관련 질문에 적합합니다.'
				},
				{
					title: 'IT Service (IT Services Office)',
					description: '해당 모델은 (itso.hkust.edu.hk)의 문서를 기반으로 답변합니다. VPN 설정 방법, 프린터기 사용 방법, 2FA 인증 등 학교 IT 서비스 관련 질문에 적합합니다.'
				},
				{
					title: 'UROP (Undergraduate Research Opportunities Program)',
					description: '해당 모델은 urop.hkust.edu.hk의 문서를 기반으로 답변합니다. UROP 신청, 이전 프로젝트 조회 등 관련 질문에 적합합니다.'
				},
                {
					title: '교환학생(Study Abroad)',
					description: '해당 모델은 studyabroad.hkust.edu.hk의 문서를 기반으로 답변합니다. 교환학생 신청 등 관련 질문에 적합합니다.'
				},
			]
		},
		{
			title: '고급 설정',
			content: [
				{
					title: '시스템 프롬프트',
					description: '시스템 프롬프트를 사용하여 모델의 동작과 응답 방식을 조정할 수 있습니다.'
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
