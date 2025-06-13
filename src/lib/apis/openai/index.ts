import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getOpenAIConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

export const updateOpenAIConfig = async (token: string = '', config: OpenAIConfig) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOpenAIUrls = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/urls`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OPENAI_API_BASE_URLS;
};

export const updateOpenAIUrls = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/urls/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			urls: urls
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OPENAI_API_BASE_URLS;
};

export const getOpenAIKeys = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/keys`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OPENAI_API_KEYS;
};

export const updateOpenAIKeys = async (token: string = '', keys: string[]) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/keys/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			keys: keys
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OPENAI_API_KEYS;
};

export const getOpenAIModelsDirect = async (url: string, key: string) => {
	let error = null;

	const res = await fetch(`${url}/models`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(key && { authorization: `Bearer ${key}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOpenAIModels = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(
		`${OPENAI_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyOpenAIConnection = async (
	token: string = '',
	connection: dict = {},
	direct: boolean = false
) => {
	const { url, key, config } = connection;
	if (!url) {
		throw 'OpenAI: URL is required';
	}

	let error = null;
	let res = null;

	if (direct) {
		res = await fetch(`${url}/models`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${key}`,
				'Content-Type': 'application/json'
			}
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
	} else {
		res = await fetch(`${OPENAI_API_BASE_URL}/verify`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				url,
				key,
				config
			})
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
	}

	return res;
};

const custombody = {
	message:
		"recette de tarte citron et couscous if you're getting the information from the chunks ,you **must ** Indicate in which chunk you found each piece of information in terms of order, and give the result in the format information §text n§\nfor example:\nL'évolution en 2019 montre une augmentation de 157% par rapport à 2018, avec un chiffre de 385 869 §text 2§\nL'évolution en 2020 montre une augmentation de xx par rapport à xx , avec un chiffre de xx §text 1§\nif you're getting the information from the images ,you **must ** Indicate in which image you found each piece of information using the filename associated with each image, and give the result in the format \" information §image filename§\"\nfor example:\nL'évolution en 2019 montre une augmentation de 157% par rapport à 2018, avec un chiffre de 385 869 §image 123123b231_148_sub_image_1.png§\nL'évolution en 2020 montre une augmentation de xx par rapport à xx , avec un chiffre de xx §image 1252a3b1123_195_sub_image_2.png§",

	mode: 'DocQuery',
	instruction:
		'You are a helpful assistant that follows the guided instructions,\nTu dois toujours répondre uniquement à partir du contexte extrait via les recherches.\nTu dois toujours répondre en utilisant la langue dans laquelle a été exprimée la question de l\'utilisateur.\n***INSTRUCTIONS :\nINSTRUCTIONS GÉNÉRALES :\n1. Adoptez systématiquement une approche de raisonnement étape par étape.\n2. Utilisez un langage clair, précis et professionnel.\n3. Assurez-vous que vos réponses sont complètes, bien structurées et exemptes d\'ambiguïtés.\nPROCESSUS DE RÉPONSE :\n1. Analyse de la requête :\n   - Tu dois toujours décomposer la question posée en étapes logiques selon une approche de raisonnement Step-by-Step\n2. Processus de recherche :\n2.1. Tu dois toujours et obligatoirement exécuter une première recherche via l\'outil de recherche sur les données client en UTILISANT la requête d\'origine sans reformulation.\n- Tu dois toujours générer 4 requêtes reformulées au minimum, tu ne dois pas dépasser 6 requêtes\n-Tu ne dois pas afficher les requêtes. \n2.2. Tu dois ensuite toujours lancer obligatoirement plusieurs les recherches granulaires via l\'outil de recherche en générant 4 requêtes reformulées au minimum  (keyword based decomposition optimized for Embedding search) couvrant toutes les notions et termes spécifiés dans la question de l\'utilisateur en suivant l\'exemple de reformulation ci-dessous :\n** Exemple de reformulation *****\nUser Query : "classification des paiements en espèces pour la partie intérêts du passif locatif dans l\'état des flux de trésorerie selon IAS 7"\nRequête 1 : for the reformulated query n°1, you have to use the original given user Query \nRequête 2 : "intérêts versés passif locatif selon IAS 7"" \nRequête 3 : "état de flux de trésorerie pour intérêts versés IFRS 16 relatif au passif locatif"\nRequête 4 : "paiements en espèces pour intérêts du passif locatif"\n- Tu dois toujours lancer les recherches associées aux requêtes reformulées, aucune réponse ne peut être générée sans recherche.\n\nif you\'re getting  the information from the chunks ,you **must ** Indicate in which chunk you found each piece of information in terms of order,and give its respective page number present in the markup <page> and give the result in the format " information §text n,page k§" \nfor example:\nL\'évolution en 2019 montre une augmentation de 157% par rapport à 2018, avec un chiffre de 385 869 §text 2, page 3§\nL\'évolution en 2020 montre une augmentation de xx par rapport à xx , avec un chiffre de xx §text 1,page 4§\nif you\'re getting  the information from the images ,you **must ** Indicate in which image you found each piece of information using the filename associated with each image, and give the result in the format " information §image filename§" \nfor example:\nL\'évolution en 2019 montre une augmentation de 157% par rapport à 2018, avec un chiffre de 385 869 §image 123123b231_148_sub_image_1.png§\nL\'évolution en 2020 montre une augmentation de xx par rapport à xx , avec un chiffre de xx §image 1252a3b1123_195_sub_image_2.png§\nThe response and the query to the tool must be in \'French\' language\nThe the query to the tool must be done using key words instead of a synthesized question\n\npour les recherches web:\n**Citation des sources\nTu dois TOUJOURS indiquer l\'URL source utilisée pour chaque recherche en utilisant le format suivant:\n🔎 <a href="[URL_COMPLETE]" target="_blank" rel="noopener">[TITRE_DESCRIPTIF]</a>\nBonnes pratiques pour les liens:\n*Utiliser un titre descriptif et pertinent pour le lien\n*Inclure target="_blank" pour ouvrir dans un nouvel onglet\n*Inclure rel="noopener" pour la sécurité\n*Placer la source immédiatement après l\'information citée\n*Si plusieurs sources sont utilisées, les grouper à la fin de la réponse',
	brain_ids: ['67fe6bf1807b8b18fb034d60'],
	questionId: '5a4a273a400ebe84mbte9buc',
	search_web: 'off',
	rag_type: 'AdvancedRag',
	isCache: '',
	metadata: {
		user_id: '67079e3c211644a5bcad854c',
		message_id: '38301db71da5b4f2mbte9buc',
		conversation_id: '683da9d06f477e987d37803d',
		mode: 'DocQuery',
		app_source: 'chat',
		username: 'Emna  Belhaj|ebelhaj@yellowsys.fr'
	},
	conversation_id: '683da9d06f477e987d37803d',
	vectorstore_name: 'vectorstoredev',
	chatbot_name: 'gpt-4o-mini',
	generate_standalone_question: 'no_history',
	enable_multilingual: false,
	mode_expert: false,
	retryCount: 0,
	chat_mode: 'streaming',
	graphml_path: '',
	languages: ['fr', 'fr'],
	synonym_list: [],
	max_tokens: 4000,
	temperature: 0,
	max_retries: 0,
	top_k: 4,
	score_seuil: 0,
	retrieval_qa_prompt:
		'\n\nContexte:\n**************\n{context}\n**************\n\nQuestion: {question}\nRéponse:',
	user_instruction: '',
	enable_rag_fusion: false,
	number_of_question: 2,
	rewording_prompt:
		'you have to decompose the following user query \n\n{question}\n\n into multi-step query optimized to be used as rag query in order to facilitate the construction of a reasoning chain.'
};

export const chatCompletion = async (
	token: string = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhemVydHkiLCJleHAiOjE3NDk3NDAwMDR9.HAAx-ltOwkAIIAi5Z_xXzhMsV8_wwWaSVUBCPx78HZ0',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;
	console.log('token', token);
	const res = await fetch(
		'https://frfrwalabaidevmetachatbotapi0001.azurewebsites.net/chatbots/chat',
		{
			signal: controller.signal,
			method: 'POST',
			headers: {
				Authorization: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhemVydHkiLCJleHAiOjE3NDk4MzEwNjV9.D2ZqCfuaYQKatUvnGrq0lDlS8R8fnO9ykoCU-OZnMzc`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(custombody)
		}
	).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const generateOpenAIChatCompletion = async (
	token: string,
	body: object,

	url: string = `${WEBUI_BASE_URL}/api`
) => {
	// Additional logging
	console.group('Generate OpenAI Chat Completion');
	console.log('Input Body:', JSON.stringify(body, null, 2));
	console.log('Custom Body Base:', JSON.stringify(custombody, null, 2));

const requestBody = JSON.parse(JSON.stringify(custombody));


	console.log('Final Request Body:', JSON.stringify(requestBody, null, 2));

	try {
		const response = await fetch(
			'https://frfrwalabaidevmetachatbotapi0001.azurewebsites.net/chatbots/chat',
			{
				method: 'POST',
				headers: {
					Authorization: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhemVydHkiLCJleHAiOjE3NDk4MzEwNjV9.D2ZqCfuaYQKatUvnGrq0lDlS8R8fnO9ykoCU-OZnMzc`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(requestBody)
			}
		);

		if (!response.ok) {
			const errorText = await response.text();
			console.error('Error Response:', errorText);
			console.groupEnd();
			throw new Error(errorText);
		}

		const contentType = response.headers.get('content-type');
		const responseData = contentType?.includes('application/json')
			? await response.json()
			: await response.text();

		console.log('Response Data:', responseData);
		console.groupEnd();

		return responseData;
	} catch (error) {
		console.error('Fetch Error:', error);
		console.groupEnd();
		throw error;
	}
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/audio/speech`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			input: text,
			voice: speaker
		})
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
