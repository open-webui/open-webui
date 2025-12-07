import { writable, derived, type Writable } from 'svelte/store';
import type { BalanceInfo, BillingLog, BillingStats } from '$lib/apis/billing';

// ========== 余额状态 ==========
export const balance: Writable<BalanceInfo | null> = writable(null);

// ========== 消费记录状态 ==========
export const billingLogs: Writable<BillingLog[]> = writable([]);

// ========== 统计数据状态 ==========
export const billingStats: Writable<BillingStats | null> = writable(null);

// ========== 派生状态：余额是否不足 ==========
export const isLowBalance = derived(balance, ($balance) => {
	if (!$balance) return false;
	// 余额单位：毫（1元 = 10000毫），低于1元（10000毫）时警告
	return $balance.balance < 10000;
});

// ========== 派生状态：账户是否冻结 ==========
export const isFrozen = derived(balance, ($balance) => {
	if (!$balance) return false;
	return $balance.billing_status === 'frozen';
});

// ========== 辅助函数：格式化金额 ==========
// amount 单位：毫（1元 = 10000毫）
export const formatCurrency = (amount: number, isCost: boolean = false): string => {
	// 转换为元：毫 / 10000
	const yuan = amount / 10000;

	// 费用支持显示 0.0001 精度（4位小数）
	// 余额等显示 2位小数
	if (isCost || yuan < 0.01) {
		// 显示4位小数，但去掉尾部的0
		return `¥${yuan.toFixed(4).replace(/\.?0+$/, '')}`;
	}

	return `¥${yuan.toFixed(2)}`;
};

// ========== 辅助函数：格式化日期 ==========
// timestamp 单位：纳秒
export const formatDate = (timestamp: number): string => {
	// 纳秒转换为毫秒：除以 1000000
	return new Date(timestamp / 1000000).toLocaleString('zh-CN', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit'
	});
};
