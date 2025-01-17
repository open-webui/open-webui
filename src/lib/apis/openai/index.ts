import { OPENAI_API_BASE_URL } from '$lib/constants';

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
			console.log(err);
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
			console.log(err);
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
			console.log(err);
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
			console.log(err);
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
			console.log(err);
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
			console.log(err);
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
	url: string = 'https://api.openai.com/v1',
	key: string = ''
) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			url,
			key
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

	return res;
};

const enrichBody = (body: object) => {
	const userMessage = body?.messages?.find(
		(message, index) =>
			message.content.includes('OpenBottomArtifacts') ||
			message.content.includes('OpenLeftArtifacts')
	);
	if (userMessage) {
		userMessage.content = userMessage.content +=
			'Use these classes, consider they already exist, do not recreate them. Use only what is necessary: /* PALLETTE White: #ffffff Extra Light Gray: #f7f7f7 Light Gray: #ededed Gray: #dfdfdf Dark Gray: #9b9b9b Extra Dark Gray: #727272 Neon green base: #77F2A1 Blue light: #C9E2FF Blue base: #1E85FF Blue dark: #021C4F Light green: #00D69D Green base: #00BC8B Light red: #FF6A71 Red base: #E90000 Light Orange: #FFB800 Orange base: #FF9600 */ ' +
			'\n Name: .nbg__support__card Description: The main container of the card with background color, border radius, padding, shadow, and flex layout. | Name: .nbg__support__card__title Description: The title of the card, styled with larger font size, bold weight, and margin at the bottom. | Name: .nbg__support__card__text Description: The description text inside the card. | Name: .nbg__support__cta__arrow Description: The CTA button with a right arrow symbol, styled for interaction. ' +
			'| Name: .nbg__blog__card Description: Main card container with background color, border-radius, padding, shadow, and layout. | Name: .nbg__blog__tags Description: Put the tags in one line horizontally | Name: .nbg__blog__tag Description: Styling for the tags (e.g., "Articles," "Artificial Intelligence"), with background color, padding, and text formatting. | Name: .nbg__blog__tag.secondary Description: Additional styling for the secondary tag, like "Artificial Intelligence," to apply a different background color. | Name: .nbg__blog__author Description: Author name styled with smaller, lighter text. | Name: .nbg__blog__title Description: Title of the blog post with larger font size and bold weight. | Name: .nbg__blog__description Description: Short description of the blog post content, styled with a smaller font size. | Name: nbg__blog__card__footer Description: the footer of the card to be in the center | Name: .nbg__blog__cta__button Description: The "Read more" button, styled with background color, padding, border-radius, and hover effect. | Name: @media screen and (max-width: 768px) Description: Adjusts the layout for smaller screens (e.g., reduces padding, font size, and makes the button full-width). ' +
			'| Name: .nbg__button Description: Base class for all buttons, defining common padding, font size, alignment, and transitions. | Name: .nbg__button__primary Description: Primary button style, green background with hover effect. | Name: .nbg__button__primary__no__fill Description: Primary button style, transparent background green letters with hover effect. | Name: .nbg__button__secondary Description: Secondary button style, blue background for dark themes with hover effect. | Name: .nbg__button__secondary__no__fill Description: Secondary button style, transparent background with blue letters with hover effect. | Name: .nbg__button__danger Description: Danger button style, red background used for delete actions with hover effect. | Name: .nbg__button__icon Description: Icon button style with a transparent background and border, commonly used for buttons with an icon. | Name: .nbg__button__text__link Description: Text link style with an underline, commonly used for hyperlinks. | Name: .nbg__button__copy Description: Copy action button with a dark background and an icon. | Name: .nbg__button__sidebar Description: Sidebar button style, typically used for sidebar navigation with full width and left-aligned text. ' +
			'| Name: .nbg__header__xl Description: Header XL style, bold, 40px font size using Work Sans. | Name: .nbg__header__lg Description: Header LG style, bold, 32px font size using Work Sans. | Name: .nbg__header Description: Default header style, regular weight, 32px font size using Work Sans. | Name: .nbg__text__xl Description: Large text style, bold, 24px font size using Work Sans. | Name: .nbg__text__lg Description: Large text style, bold, 18px font size using Manrope. | Name: .nbg__text__base Description: Base text style, regular weight, 18px font size using Manrope. | Name: .nbg__text__sm Description: Small text style, regular weight, 14px font size using Work Sans. | Name: .nbg__text__xs Description: Extra small text style, regular weight, 12px font size using Work Sans. | Name: .nbg__text__xs__code Description: Extra small code block style, regular weight, 12px font size using Fira Code. ' +
			'| Name: .nbg__step__card Description: Basic styling for the step card, with padding, background color, border-radius, text alignment, and flex layout. | Name: .nbg__step__card__left Description: Applies left alignment to the card content. | Name: .nbg__step__card__number Description: Styles for the step number, creating a circle with background color and center-aligned text. | Name: .nbg__step__card__description Description: Styling for the description text inside the card. | Name: @media screen and (max-width: 768px) Description: Adjusts the card’s layout for smaller screen sizes, including the number size, font size of the description, and card padding. ' +
			'| Name: .nbg__feature__card Description: This is the container for the feature card, which includes padding, background color, border-radius, shadow, and width properties. | Name: .nbg__feature__card__title Description: Styles for the title of the card, including font size, weight, and margin. | Name: .nbg__feature__card__button Description: Styling for the button within the card (e.g., "Account Information"), with transparent background, border, and hover effect. | Name: .nbg__feature__card__description Description: Description of the feature card, styled with a smaller font size and lighter text color. | Name: @media screen and (max-width: 768px) Description: Adjustments for smaller screen sizes, including font size, padding, and button width for better readability and usability on mobile devices. The CTA is between the title and the description. ' +
			'| Name: .nbg__advantage__card Description: The main container for the card, with background color, padding, border-radius, shadow, and margin. | Name: .nbg__advantage__card__title Description: The title of the card styled with a larger font size and bold weight. | Name: .nbg__advantage__card__tag Description: The tag label (e.g., "PSD2 Directive") that is styled with a background color, border radius, and uppercase text. | Name: .nbg__advantage__card__description Description: The descriptive text inside the card, with a smaller font size and different color to distinguish it from the title. | Name: .nbg__advantage__card__list Description: A styled list to display services with a decimal style. | Name: .nbg__advantage__card__list-item Description: Each list item, styled with a font size and spacing. | Name: @media screen and (max-width: 768px) Description: This section adjusts the card layout for smaller screens, such as reducing padding, adjusting font size, and ensuring better legibility and layout for mobile devices.';
	}
	return body;
};

export const generateOpenAIChatCompletion = async (
	token: string = '',
	body: object,
	url: string = OPENAI_API_BASE_URL
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${url}/chat/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(enrichBody(body))
	}).catch((err) => {
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
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
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
