<script lang="ts">
	import { setContext } from 'svelte';
	import { writable } from 'svelte/store';
	import { createInstance } from 'i18next';
	import { config, mobile, models, settings, user } from '$lib/stores';
	import Message from '$lib/components/chat/Messages/Message.svelte';
	import en from '$lib/i18n/locales/en-GB/translation.json';
	import fr from '$lib/i18n/locales/fr-CA/translation.json';

	const params = new URLSearchParams(location.search);
	const locale = params.get('locale') || 'en-GB';
	document.documentElement.lang = locale.startsWith('fr') ? 'fr-CA' : 'en-GB';
	const multi = params.has('multi');
	const i18n = createInstance();
	i18n.init({
		lng: locale,
		fallbackLng: 'en-GB',
		returnEmptyString: false,
		resources: { 'en-GB': { translation: en }, 'fr-CA': { translation: fr } }
	});
	setContext('i18n', writable(i18n));
	mobile.set(window.innerWidth < 768);
	settings.set({ chatBubble: !params.has('no-bubbles') });
	user.set({
		id: 'reflow-user',
		name: 'Alex',
		email: '',
		role: 'admin',
		profile_image_url: '/user.png'
	});
	config.set({
		status: true,
		name: 'CANChat',
		version: 'test',
		default_locale: locale,
		default_models: 'alpha',
		default_prompt_suggestions: [],
		docs_url: '',
		docs_url_fr: '',
		survey_url: '',
		survey_url_fr: '',
		oauth: { providers: {} },
		features: {
			auth: false,
			auth_trusted_header: false,
			enable_api_key: false,
			enable_signup: false,
			enable_login_form: false,
			enable_google_drive_integration: false,
			enable_image_generation: true,
			enable_admin_export: false,
			enable_admin_chat_access: false,
			enable_community_sharing: false
		}
	});
	const model = {
		id: 'alpha',
		name: 'Example assistant model with a long descriptive name',
		owned_by: 'openai' as const,
		external: false,
		actions: [{ id: 'custom-action', name: 'Custom action' }]
	};
	models.set([model, { ...model, id: 'beta', name: 'Second assistant' }]);

	const content = [
		'A response with ordinary prose that should wrap without horizontal scrolling.',
		`[${'long-link-'.repeat(12)}](https://example.test/)`,
		'| First column | Second column | Third column |\n| --- | --- | --- |\n| Data | Data | Data |',
		'```text\n' + 'Long code line '.repeat(20) + '\n```'
	].join('\n\n');
	const response = {
		id: 'response',
		parentId: 'prompt',
		childrenIds: [],
		role: 'assistant',
		model: 'alpha',
		modelIdx: 0,
		content,
		timestamp: 1700000000,
		done: true,
		usage: { total_tokens: 100 }
	};
	let history = {
		currentId: 'response',
		messages: {
			prompt: {
				id: 'prompt',
				parentId: null,
				childrenIds: multi ? ['response', 'alternative'] : ['response', 'branch'],
				models: multi ? ['alpha', 'beta'] : ['alpha'],
				role: 'user',
				content: 'A message to edit at a narrow viewport.',
				timestamp: 1700000000
			},
			response,
			branch: { ...response, id: 'branch' },
			alternative: { ...response, id: 'alternative', model: 'beta', modelIdx: 1 }
		}
	};
	const noop = () => {};
	let regenerated = 0;
	const messageProps = {
		chatId: 'reflow',
		user: { name: 'Alex' },
		updateChat: noop,
		editMessage: noop,
		saveMessage: noop,
		deleteMessage: noop,
		rateMessage: noop,
		actionMessage: noop,
		submitMessage: noop,
		continueResponse: noop,
		regenerateResponse: () => {
			regenerated++;
		},
		mergeResponses: noop,
		addMessages: noop,
		triggerScroll: noop,
		showPreviousMessage: noop,
		showNextMessage: noop
	};
</script>

<main>
	<Message {...messageProps} idx={0} {history} messageId="prompt" />
	<Message {...messageProps} idx={1} bind:history messageId="response" />
	<output aria-label="Regenerations">{regenerated}</output>
</main>
