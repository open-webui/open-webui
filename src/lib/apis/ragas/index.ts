import { RAGAS_API_BASE_URL } from '$lib/constants';


type RagasSettings = {
	ENABLE_RAGAS:boolean |false;
    ragasEvalLogsPath: string | null;
    ragasEvalFilePath: string | null;
};

export const getRagasConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${RAGAS_API_BASE_URL}/config`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};


export const eraseQA = async (token: string) => {
	let error = null;

	const res = await fetch(`${RAGAS_API_BASE_URL}/erase_qa`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getRagasEvalConfig = async (token: string) => {
	let error = null;
	console.log("getting ragas eval config on "+RAGAS_API_BASE_URL+"/eval_config")

	const res = await fetch(`${RAGAS_API_BASE_URL}/eval_config`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type EvalSettings = {
    question:Array<string>;
    ground_truth: Array<string>;
	documentId:Array<string>;
	modelId:Array<string>;
	answer:Array<string>;
};

export const updateRagasEvalConfig = async (token: string, settings: EvalSettings) => {
	let error = null;
    console.log("Update with ",settings)
	
	const res = await fetch(`${RAGAS_API_BASE_URL}/config/update_eval`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...settings
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
	
};



export const updateRagasSettings = async (token: string, settings: RagasSettings) => {
	let error = null;
    console.log("Settings ",settings)
	
	const res = await fetch(`${RAGAS_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...settings
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
	
};

/** 
export const ragasEval = async (token: string) => {
	let error = null;

	const res = await fetch(`${RAGAS_API_BASE_URL}/eval/ragas`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
**/
