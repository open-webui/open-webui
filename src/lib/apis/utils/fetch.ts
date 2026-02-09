import { goto } from '$app/navigation';
import { user } from '$lib/stores';
import { toast } from 'svelte-sonner';

/**
 * 全局 401 錯誤處理器
 * 當 token 過期時自動清除本地狀態並重定向到登入頁面
 */
export const handle401Error = async () => {
	// 清除本地 token
	localStorage.removeItem('token');

	// 清除 user store
	user.set(undefined);

	// 顯示提示訊息
	toast.error('Session expired. Please sign in again.');

	// 重定向到登入頁面，保留當前路徑用於登入後跳回
	const encodedUrl = encodeURIComponent(window.location.pathname);
	await goto(`/auth?redirect=${encodedUrl}`);
};

/**
 * 檢查錯誤是否為 401 錯誤，若是則自動處理
 * @param error - 捕獲到的錯誤物件
 * @returns 是否為 401 錯誤並已處理
 */
export const checkAndHandle401 = async (error: any): Promise<boolean> => {
	// 檢查錯誤是否包含 401 相關信息
	if (
		error?.status === 401 ||
		error?.detail?.includes?.('Not authenticated') ||
		error?.detail?.includes?.('Invalid token') ||
		error?.detail?.includes?.('Token expired') ||
		error?.detail === 'Unauthorized'
	) {
		await handle401Error();
		return true;
	}
	return false;
};
