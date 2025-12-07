import { WEBUI_API_BASE_URL } from '$lib/constants';

// ========== 类型定义 ==========

export interface BalanceInfo {
	balance: number;
	total_consumed: number;
	billing_status: 'active' | 'frozen';
}

export interface BillingLog {
	id: string;
	model_id: string;
	cost: number;
	balance_after: number | null;
	type: 'deduct' | 'refund' | 'precharge' | 'settle';
	prompt_tokens: number;
	completion_tokens: number;
	created_at: number;
	precharge_id?: string | null; // 预扣费事务ID，用于关联 precharge 和 settle
}

export interface DailyStats {
	date: string;
	cost: number;
}

export interface ModelStats {
	model: string;
	cost: number;
	count: number;
}

export interface BillingStats {
	daily: DailyStats[];
	by_model: ModelStats[];
}

export interface ModelPricing {
	model_id: string;
	input_price: number;
	output_price: number;
	source: 'database' | 'default';
}

export interface RechargeRequest {
	user_id: string;
	amount: number;
	remark?: string;
}

export interface RechargeLog {
	id: string;
	user_id: string;
	amount: number;
	operator_id: string;
	operator_name: string;
	remark: string | null;
	created_at: number;
}

// ========== API函数 ==========

/**
 * 查询当前用户余额
 */
export const getBalance = async (token: string): Promise<BalanceInfo> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/balance`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 查询消费记录
 */
export const getBillingLogs = async (
	token: string,
	limit: number = 50,
	offset: number = 0
): Promise<BillingLog[]> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/billing/logs?limit=${limit}&offset=${offset}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 查询统计报表
 */
export const getBillingStats = async (
	token: string,
	days: number = 7
): Promise<BillingStats> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/stats?days=${days}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 查询模型定价
 */
export const getModelPricing = async (modelId: string): Promise<ModelPricing> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/pricing/${modelId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 列出所有模型定价
 */
export const listModelPricing = async (): Promise<ModelPricing[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/pricing`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 管理员充值（仅管理员）
 */
export const rechargeUser = async (
	token: string,
	data: RechargeRequest
): Promise<{ balance: number; status: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/recharge`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 设置模型定价（仅管理员）
 */
export const setModelPricing = async (
	token: string,
	data: { model_id: string; input_price: number; output_price: number }
): Promise<ModelPricing> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/billing/pricing`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 查询用户充值记录 (仅管理员)
 */
export const getRechargeLogsByUserId = async (
	token: string,
	userId: string,
	limit: number = 50,
	offset: number = 0
): Promise<RechargeLog[]> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/billing/recharge/logs/${userId}?limit=${limit}&offset=${offset}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
