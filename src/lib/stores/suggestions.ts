import { writable, get } from 'svelte/store';
import {
	getMyTopTags,
	getGlobalTopTags,
	setTagFeedback,
	type TagWithFeedback,
	type FeedbackStatus
} from '$lib/apis/message-tags';

// Store 상태
const personalTopTags = writable<TagWithFeedback[]>([]);
const globalTopTags = writable<TagWithFeedback[]>([]);
const loading = writable(false);

// 데이터 로드 여부 추적 (API 호출 최소화)
let personalTagsLoaded = false;
let globalTagsLoaded = false;

/**
 * 개인 상위 태그 로드 (캐시된 데이터가 없을 때만 API 호출)
 */
async function loadPersonalTopTags(token: string, limit: number = 3, force: boolean = false) {
	if (personalTagsLoaded && !force) {
		return get(personalTopTags);
	}

	loading.set(true);
	try {
		const tags = await getMyTopTags(token, limit);
		if (tags) {
			personalTopTags.set(tags);
			personalTagsLoaded = true;
		}
		return tags;
	} catch (err) {
		console.error('Failed to load personal top tags:', err);
		return null;
	} finally {
		loading.set(false);
	}
}

/**
 * 전역 상위 태그 로드 (캐시된 데이터가 없을 때만 API 호출)
 */
async function loadGlobalTopTags(token: string, limit: number = 3, force: boolean = false) {
	if (globalTagsLoaded && !force) {
		return get(globalTopTags);
	}

	loading.set(true);
	try {
		const tags = await getGlobalTopTags(token, limit);
		if (tags) {
			globalTopTags.set(tags);
			globalTagsLoaded = true;
		}
		return tags;
	} catch (err) {
		console.error('Failed to load global top tags:', err);
		return null;
	} finally {
		loading.set(false);
	}
}

/**
 * 태그에 피드백 설정 후 부드럽게 목록 업데이트
 */
async function submitFeedback(
	token: string,
	tagId: string,
	status: FeedbackStatus,
	isPersonalized: boolean,
	limit: number = 3
) {
	const store = isPersonalized ? personalTopTags : globalTopTags;

	// 1. 낙관적 업데이트: 피드백 상태만 먼저 업데이트
	store.update((tags) =>
		tags.map((t) => (t.id === tagId ? { ...t, feedback_status: status } : t))
	);

	try {
		// 2. 서버에 피드백 저장
		await setTagFeedback(token, tagId, status);

		// 3. 백그라운드에서 새 목록 가져오기
		const newTags = isPersonalized
			? await getMyTopTags(token, limit)
			: await getGlobalTopTags(token, limit);

		if (newTags) {
			// 4. 부드러운 업데이트: 기존 태그와 새 태그 비교하여 점진적으로 업데이트
			store.update((currentTags) => {
				const existingIds = new Set(currentTags.map((t) => t.id));
				const newIds = new Set(newTags.map((t) => t.id));

				// 제거된 태그 필터링
				let updatedTags = currentTags.filter((t) => newIds.has(t.id));

				// 새로운 태그 추가
				const tagsToAdd = newTags.filter((t) => !existingIds.has(t.id));
				updatedTags = [...updatedTags, ...tagsToAdd];

				// 서버 순서대로 정렬
				const orderMap = new Map(newTags.map((t, i) => [t.id, i]));
				updatedTags.sort((a, b) => (orderMap.get(a.id) || 0) - (orderMap.get(b.id) || 0));

				return updatedTags;
			});

			// 캐시 상태 업데이트
			if (isPersonalized) {
				personalTagsLoaded = true;
			} else {
				globalTagsLoaded = true;
			}
		}
	} catch (err) {
		console.error('Failed to set feedback:', err);
	}
}

/**
 * 특정 태그 목록 무효화 (다음 접근 시 새로 로드)
 */
function invalidatePersonalTags() {
	personalTagsLoaded = false;
}

function invalidateGlobalTags() {
	globalTagsLoaded = false;
}

/**
 * 모든 태그 목록 무효화
 */
function invalidateAll() {
	personalTagsLoaded = false;
	globalTagsLoaded = false;
}

/**
 * store 초기화 (로그아웃 시 사용)
 */
function reset() {
	personalTopTags.set([]);
	globalTopTags.set([]);
	personalTagsLoaded = false;
	globalTagsLoaded = false;
}

export const suggestionsStore = {
	personalTopTags,
	globalTopTags,
	loading,
	loadPersonalTopTags,
	loadGlobalTopTags,
	submitFeedback,
	invalidatePersonalTags,
	invalidateGlobalTags,
	invalidateAll,
	reset
};
