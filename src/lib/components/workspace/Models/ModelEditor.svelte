<script lang="ts">
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { beforeNavigate, goto } from '$app/navigation';
	import { getModels } from '$lib/apis';
	import ModelHistory from './ModelHistory.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { config, models, tools, functions, user, settings } from '$lib/stores';
	import { WEBUI_BASE_URL, DEFAULT_CAPABILITIES } from '$lib/constants';

	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { getFunctions } from '$lib/apis/functions';
	import { getModelsDefaults } from '$lib/apis/configs';
	import { getLanguages } from '$lib/i18n';
	import {
		getBaseModelTags,
		getModelTags,
		type ModelHistoryEntry,
		type ModelSnapshot
	} from '$lib/apis/models';
	import { getVoices } from '$lib/apis/audio';
	import { uploadFile, deleteFileById } from '$lib/apis/files';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import ModelControls from '$lib/components/admin/Settings/Models/ModelControls.svelte';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import SkillsSelector from '$lib/components/workspace/Models/SkillsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ModelSettingsSection from './ModelSettingsSection.svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import LocalizedPromptSuggestions from './LocalizedPromptSuggestions.svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';
	import TerminalSelector from './TerminalSelector.svelte';
	import TTSVoiceInput from './TTSVoiceInput.svelte';
	import VoiceAvatarSettings from './VoiceAvatarSettings.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import {
		avatarAssetIds,
		type AnimationFiles,
		type VoiceAvatarConfig
	} from '$lib/utils/voice-avatar';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import { copyToClipboard, extractInputVariables } from '$lib/utils';
	import {
		modelControlTranslationSource,
		pruneEmptyLocaleEntries
	} from '$lib/utils/localizedContent';
	import TranslationTable from '$lib/components/common/TranslationTable.svelte';

	const i18n: any = getContext('i18n');
	const formId = `model-editor-${uuidv4()}`;

	export let onSubmit: Function = () => {};
	export let readOnly = false;
	export let onBack: null | Function = null;

	export let model: any = null;
	export let edit = false;
	export let admin = false;

	export let preset = true;

	let loading = false;
	let historyMenu: ModelHistory;
	let selectedVersion: (ModelHistoryEntry & { snapshot: ModelSnapshot }) | null = null;
	let selectingVersion = false;
	let promotingVersion = false;
	$: historical = !!selectedVersion || selectingVersion;
	let commitMessage = '';
	let savedDraft = '';
	let defaultMeta: Record<string, any> = {};
	let allowNavigation = false;
	let showDiscard = false;
	let afterDiscard: (() => void) | null = null;
	$: configurationChanged =
		!!savedDraft &&
		(JSON.stringify(modelInfo) !== savedDraft ||
			!!backgroundFile ||
			!!avatarFile ||
			Object.keys(animationFiles).length > 0);
	$: dirty = configurationChanged || (!!savedDraft && !!commitMessage);
	const discardThen = (action: () => void) => {
		if (!dirty) return action();
		afterDiscard = action;
		showDiscard = true;
	};
	beforeNavigate(({ cancel, to, willUnload }) => {
		if (readOnly || !dirty || allowNavigation) return;
		cancel();
		if (!willUnload && to)
			discardThen(() => {
				allowNavigation = true;
				goto(to.url.href);
			});
	});

	let voiceAvatar: VoiceAvatarConfig | null = null;
	let avatarFile: File | null = null;
	let animationFiles: AnimationFiles = {};
	let backgroundFile: File | null = null;
	let backgroundInput: HTMLInputElement;
	let backgroundPreview: string | null = null;
	const clearBackgroundPreview = () => {
		if (backgroundPreview) URL.revokeObjectURL(backgroundPreview);
		backgroundPreview = null;
	};
	onDestroy(clearBackgroundPreview);
	let success = false;

	let filesInputElement;
	let inputFiles;

	let showSystemPrompt = true;
	let showAdvanced = false;
	let showPreview = false;
	let customPromptDraft: any[] | null = null;
	let showAccessControlModal = false;

	let loaded = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';
	let languages: { code: string; title: string }[] = [];
	let editingLocale = '';

	let enableDescription = true;

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	let system = '';
	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			// LICENSE covers this Open WebUI fallback logo.
			// Do not alter, remove, obscure, or replace it except as LICENSE permits:
			// https://docs.openwebui.com/license.
			profile_image_url: `${WEBUI_BASE_URL}/static/favicon.png`,
			background_image_url: null as string | null,
			voice: undefined as { voice?: string } | undefined,
			voice_avatar: null as VoiceAvatarConfig | null,
			description: '',
			i18n: {},
			suggestion_prompts: null,
			tags: []
		},
		params: {
			system: ''
		}
	};

	let params: Record<string, any> = {
		system: ''
	};

	$: modifiedParamCount = Object.entries(params).reduce((count, [key, value]) => {
		if (key === 'system' || key === 'model_controls') return count;
		if (key === 'custom_params') {
			return count + Object.keys(value ?? {}).filter((name) => name.trim()).length;
		}
		return count + (value != null && value !== '' ? 1 : 0);
	}, 0);

	let knowledge = [];
	let toolIds = [];
	let skillIds = [];
	let skillsList = [];

	let filterIds = [];
	let defaultFilterIds = [];

	let capabilities = { ...DEFAULT_CAPABILITIES };
	let defaultFeatureIds = [];
	let builtinTools = {};

	let actionIds = [];
	let accessGrants = [];
	let terminalId = '';
	let tts = { voice: '' };
	let voice = { voice: '' };
	export let suggestionTags: { name: string }[] = [];
	let voices: { id: string; name?: string }[] = [];

	$: translatedLocales = Object.entries(info?.meta?.i18n ?? {})
		.filter(([_, value]: [string, any]) => Object.keys(value ?? {}).length > 0)
		.map(([locale]) => locale);
	$: editingLocaleLabel = languages.find((language) => language.code === editingLocale)?.title;
	const isControlTranslation = (key: string) => key.startsWith('model_controls.');
	$: controlTranslations = Object.fromEntries(
		Object.entries((info?.meta?.i18n?.[editingLocale] ?? {}) as Record<string, string>).filter(
			([key]) => isControlTranslation(key)
		)
	);

	const localizedField = (field: string) => info?.meta?.i18n?.[editingLocale]?.[field] ?? '';
	const setLocalizedField = (field: string, value: string) => {
		if (!editingLocale) return;

		info.meta.i18n = {
			...(info.meta.i18n ?? {}),
			[editingLocale]: {
				...(info.meta.i18n?.[editingLocale] ?? {}),
				[field]: value
			}
		};
		info = info;
	};

	const clearLocalizedField = (field: string) => {
		if (!editingLocale || !info.meta.i18n?.[editingLocale]) return;

		const nextLocale = { ...info.meta.i18n[editingLocale] };
		delete nextLocale[field];

		const nextI18n = { ...(info.meta.i18n ?? {}) };
		if (Object.keys(nextLocale).length === 0) {
			delete nextI18n[editingLocale];
		} else {
			nextI18n[editingLocale] = nextLocale;
		}

		info.meta.i18n = nextI18n;
		info = info;
	};

	const setControlTranslations = (next: Record<string, string>) => {
		const otherFields = Object.entries(info.meta.i18n?.[editingLocale] ?? {}).filter(
			([key]) => !isControlTranslation(key)
		);
		info.meta.i18n = {
			...(info.meta.i18n ?? {}),
			[editingLocale]: { ...Object.fromEntries(otherFields), ...next }
		};
		info = info;
	};

	const chatVariableKeyRegex = /^[a-z][a-z0-9_]*$/;
	const getChatVariablesPreview = (prompt: string) => {
		const variables = extractInputVariables(prompt);
		const warnings: string[] = [];
		const seenDefinitions: Record<string, string> = {};
		const typedRegex = /{{\s*chat\.variables\.([a-zA-Z0-9_.-]+)\s*\|\s*([^}]*)\s*}}/g;
		const typedUserRegex = /{{\s*user\.variables\.([a-zA-Z0-9_.-]+)\s*\|\s*([^}]*)\s*}}/g;

		for (const match of prompt.matchAll(typedRegex)) {
			const key = match[1];
			const definition = match[2].trim();
			if (seenDefinitions[key] && seenDefinitions[key] !== definition) {
				warnings.push(`${key} has conflicting duplicate definitions`);
			}
			seenDefinitions[key] = definition;
		}

		const fields = Object.entries(variables)
			.filter(([name]) => name.startsWith('chat.variables.'))
			.map(([name, field]) => ({ key: name.replace('chat.variables.', ''), ...(field as any) }));
		const userFields = Object.entries(variables)
			.filter(([name]) => name.startsWith('user.variables.'))
			.map(([name]) => ({ key: name.replace('user.variables.', '') }));

		for (const match of prompt.matchAll(typedUserRegex)) {
			warnings.push(`${match[1]} uses metadata, but User Variables are configured by each user`);
		}

		for (const field of fields) {
			const key = field.key;
			if (!chatVariableKeyRegex.test(key)) {
				warnings.push(`${key} must be lowercase snake case`);
				continue;
			}

			if (
				field.type === 'select' &&
				(!Array.isArray(field.options) || field.options.length === 0)
			) {
				warnings.push(`${key} select needs options=[...]`);
			}
		}

		for (const field of userFields) {
			if (!chatVariableKeyRegex.test(field.key)) {
				warnings.push(`${field.key} must be lowercase snake case`);
			}
		}

		return { fields, userFields, warnings };
	};

	$: chatVariablesPreview = getChatVariablesPreview(system ?? '');

	const getBaseModelItems = (models: any[] = []) => {
		const currentModelId = (model as any)?.id;

		return models
			.filter(
				(baseModel) =>
					(!currentModelId ||
						baseModel.id !== currentModelId ||
						(edit && baseModel.id === info.base_model_id)) &&
					(!baseModel?.preset || (edit && baseModel.id === info.base_model_id)) &&
					baseModel?.owned_by !== 'arena' &&
					!(baseModel?.direct ?? false) &&
					($user?.role === 'admin' ||
						!(baseModel?.info?.meta?.hidden ?? false) ||
						baseModel.id === info.base_model_id)
			)
			.map((baseModel) => ({
				value: baseModel.id,
				label: baseModel.name,
				model: baseModel
			}));
	};

	const loadSuggestionTags = async () => {
		const res: string[] = await (preset ? getModelTags : getBaseModelTags)(
			localStorage.token
		).catch(() => []);
		suggestionTags = res.map((tag) => ({ name: tag }));
	};

	const loadVoices = async () => {
		const res = await getVoices(localStorage.token).catch(() => null);
		voices = res?.voices ?? [];
	};

	const toModelKnowledgeReference = (item: any) => {
		if (!item || typeof item !== 'object') {
			return item;
		}

		return Object.fromEntries(
			[
				'id',
				'name',
				'type',
				'description',
				'context',
				'legacy',
				'collection_name',
				'collection_names'
			]
				.filter((key) => item[key] !== undefined && item[key] !== null && item[key] !== '')
				.map((key) => [key, item[key]])
		);
	};

	$: modelInfo = (() => {
		const modelInfo = structuredClone(info);

		modelInfo.id = id;
		modelInfo.meta.voice_avatar = voiceAvatar;
		modelInfo.name = name;

		modelInfo.params = { ...modelInfo.params, ...params };

		modelInfo.access_grants = accessGrants;
		modelInfo.meta.capabilities = capabilities;

		if (enableDescription) {
			modelInfo.meta.description =
				(modelInfo.meta.description ?? '').trim() === '' ? null : modelInfo.meta.description;
		} else {
			modelInfo.meta.description = null;
		}

		if (knowledge.length > 0) {
			modelInfo.meta.knowledge = knowledge.map(toModelKnowledgeReference);
		} else {
			if (modelInfo.meta.knowledge) {
				delete modelInfo.meta.knowledge;
			}
		}

		if (toolIds.length > 0) {
			modelInfo.meta.toolIds = toolIds;
		} else {
			if (modelInfo.meta.toolIds) {
				delete modelInfo.meta.toolIds;
			}
		}

		if (skillIds.length > 0) {
			modelInfo.meta.skillIds = skillIds;
		} else {
			if (modelInfo.meta.skillIds) {
				delete modelInfo.meta.skillIds;
			}
		}

		if (filterIds.length > 0) {
			modelInfo.meta.filterIds = filterIds;
		} else {
			if (modelInfo.meta.filterIds) {
				delete modelInfo.meta.filterIds;
			}
		}

		if (defaultFilterIds.length > 0) {
			modelInfo.meta.defaultFilterIds = defaultFilterIds;
		} else {
			if (modelInfo.meta.defaultFilterIds) {
				delete modelInfo.meta.defaultFilterIds;
			}
		}

		if (actionIds.length > 0) {
			modelInfo.meta.actionIds = actionIds;
		} else {
			if (modelInfo.meta.actionIds) {
				delete modelInfo.meta.actionIds;
			}
		}

		if (defaultFeatureIds.length > 0) {
			modelInfo.meta.defaultFeatureIds = defaultFeatureIds;
		} else {
			if (modelInfo.meta.defaultFeatureIds) {
				delete modelInfo.meta.defaultFeatureIds;
			}
		}

		if (Object.keys(builtinTools).length > 0) {
			modelInfo.meta.builtinTools = builtinTools;
		} else {
			if (modelInfo.meta.builtinTools) {
				delete modelInfo.meta.builtinTools;
			}
		}

		modelInfo.meta.i18n = pruneEmptyLocaleEntries(modelInfo.meta.i18n);
		if (Object.keys(modelInfo.meta.i18n).length === 0) {
			delete modelInfo.meta.i18n;
		}

		if (terminalId) {
			modelInfo.meta.terminalId = terminalId;
		} else {
			if (modelInfo.meta.terminalId) {
				delete modelInfo.meta.terminalId;
			}
		}

		if (voice.voice.trim()) modelInfo.meta.voice = { voice: voice.voice.trim() };
		else delete modelInfo.meta.voice;

		if (tts.voice !== '') {
			if (!modelInfo.meta.tts) modelInfo.meta.tts = {};
			modelInfo.meta.tts.voice = tts.voice;
		} else {
			if (modelInfo.meta.tts?.voice) {
				delete modelInfo.meta.tts.voice;
				if (Object.keys(modelInfo.meta.tts).length === 0) {
					delete modelInfo.meta.tts;
				}
			}
		}

		modelInfo.params.system = system.trim() === '' ? null : system;
		modelInfo.params.stop = params.stop
			? (typeof params.stop === 'string' ? params.stop.split(',') : params.stop).filter((s) =>
					s.trim()
				)
			: null;
		Object.keys(modelInfo.params).forEach((key) => {
			if (modelInfo.params[key] === '' || modelInfo.params[key] === null) {
				delete modelInfo.params[key];
			}
		});

		return modelInfo;
	})();

	const preventReadOnlyEdit = (event: Event) => {
		if (readOnly && event.target instanceof Element && event.target.closest('fieldset:disabled')) {
			if (event instanceof KeyboardEvent && event.key === 'Tab') return;
			event.preventDefault();
			event.stopPropagation();
		}
	};

	const submitHandler = async () => {
		if (readOnly || loading || historical || (edit && !configurationChanged)) return;
		loading = true;

		if (id === '') {
			toast.error($i18n.t('Model ID is required.'));
			loading = false;

			return;
		}

		if (/\s/.test(id)) {
			toast.error($i18n.t('Model ID cannot contain whitespace.'));
			loading = false;

			return;
		}

		if (name === '') {
			toast.error($i18n.t('Model Name is required.'));
			loading = false;

			return;
		}

		if (preset && !info.base_model_id) {
			toast.error($i18n.t('Base Model is required.'));
			loading = false;

			return;
		}

		if (knowledge.some((item) => item.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;

			return;
		}

		info = structuredClone(modelInfo);

		let saveAttempted = false;
		let uploadedId: string | null = null;
		const previousBackground = info.meta.background_image_url;
		const previousAvatar = structuredClone(info.meta.voice_avatar);
		const uploadedAvatarIds: string[] = [];

		try {
			if (backgroundFile) {
				const uploaded = await uploadFile(localStorage.token, backgroundFile, null, false, false);
				if (!uploaded?.id) throw new Error($i18n.t('Failed to upload background image.'));
				uploadedId = uploaded.id;
				info.meta.background_image_url = `/api/v1/files/${uploaded.id}/content`;
			}
			if (avatarFile && info.meta.voice_avatar) {
				const uploaded = await uploadFile(localStorage.token, avatarFile, null, false, false);
				if (!uploaded?.id) throw new Error($i18n.t('Failed to upload avatar.'));
				uploadedAvatarIds.push(uploaded.id);
				info.meta.voice_avatar = { ...info.meta.voice_avatar, file_id: uploaded.id };
			}
			if (info.meta.voice_avatar) {
				const avatar = info.meta.voice_avatar;
				const replacements = new Map<string, string>();
				for (const id of new Set(avatarAssetIds(avatar))) {
					if (!animationFiles[id]) continue;
					const uploaded = await uploadFile(
						localStorage.token,
						animationFiles[id],
						null,
						false,
						false
					);
					if (!uploaded?.id) throw new Error($i18n.t('Failed to upload animation.'));
					uploadedAvatarIds.push(uploaded.id);
					replacements.set(id, uploaded.id);
				}
				for (const asset of [...Object.values(avatar.states ?? {}), ...(avatar.gestures ?? [])]) {
					asset.file_id = replacements.get(asset.file_id) ?? asset.file_id;
				}
			}
			saveAttempted = true;
			allowNavigation = true;
			const saved = await onSubmit({ ...info, commit_message: commitMessage || undefined });
			if (!saved) throw new Error($i18n.t('Failed to save model'));
			if (typeof saved === 'object') await loadModel(saved);
			commitMessage = '';
			backgroundFile = null;
			avatarFile = null;
			animationFiles = {};
			voiceAvatar = info.meta.voice_avatar;
			clearBackgroundPreview();
			await tick();
			savedDraft = JSON.stringify(modelInfo);
			allowNavigation = false;
		} catch (error: any) {
			info.meta.background_image_url = previousBackground;
			info.meta.voice_avatar = previousAvatar;
			allowNavigation = false;
			// A lost response can follow a committed version. Keep its uploads until the outcome is known.
			if (!saveAttempted) {
				for (const fileId of [...uploadedAvatarIds, ...(uploadedId ? [uploadedId] : [])]) {
					await deleteFileById(localStorage.token, fileId).catch(() => {});
				}
			}

			toast.error(`${error?.detail ?? error?.message ?? error}`);
		} finally {
			loading = false;
			success = false;
		}
	};

	const loadModel = async (value: any) => {
		customPromptDraft = null;
		model = value ? structuredClone(value) : null;
		backgroundFile = null;
		avatarFile = null;
		animationFiles = {};
		commitMessage = '';
		editingLocale = '';
		clearBackgroundPreview();
		if (model) {
			model.meta ??= {};
			name = model.name;
			voiceAvatar = model.meta?.voice_avatar ? structuredClone(model.meta.voice_avatar) : null;
			await tick();

			id = model.id;

			enableDescription = model?.meta?.description !== null;

			if (model.base_model_id) {
				const base_model = $models
					.filter(
						(m) => (!m?.preset && !(m?.arena ?? false)) || (edit && m.id === model.base_model_id)
					)
					.find((m) => [model.base_model_id, `${model.base_model_id}:latest`].includes(m.id));

				console.log('base_model', base_model);

				if (base_model) {
					model.base_model_id = base_model.id;
				} else if (!edit) {
					model.base_model_id = null;
				}
			}

			system = model?.params?.system ?? '';
			showSystemPrompt = !system.trim();

			params = { system: '', ...model?.params };
			params.stop = params?.stop
				? (typeof params.stop === 'string' ? params.stop.split(',') : (params?.stop ?? [])).join(
						','
					)
				: null;

			knowledge = (model?.meta?.knowledge ?? []).map((item) => {
				if (item?.collection_name && item?.type !== 'file') {
					return {
						id: item.collection_name,
						name: item.name,
						legacy: true
					};
				} else if (item?.collection_names) {
					return {
						name: item.name,
						type: 'collection',
						collection_names: item.collection_names,
						legacy: true
					};
				} else {
					return item;
				}
			});

			toolIds = model?.meta?.toolIds ?? [];
			skillIds = model?.meta?.skillIds ?? [];
			filterIds = model?.meta?.filterIds ?? [];
			defaultFilterIds = model?.meta?.defaultFilterIds ?? [];
			actionIds = model?.meta?.actionIds ?? [];

			// Per-model overrides take precedence over admin defaults
			capabilities = {
				...DEFAULT_CAPABILITIES,
				...(defaultMeta.capabilities ?? {}),
				...(model?.meta?.capabilities ?? {})
			};
			defaultFeatureIds = model?.meta?.defaultFeatureIds ?? defaultMeta.defaultFeatureIds ?? [];
			builtinTools = model?.meta?.builtinTools ?? defaultMeta.builtinTools ?? {};
			terminalId = model?.meta?.terminalId ?? '';
			tts = { voice: model?.meta?.tts?.voice ?? '' };
			voice = { voice: model?.meta?.voice?.voice ?? '' };

			accessGrants = model?.access_grants ?? [];

			info = structuredClone(model);
			info.meta.i18n = info.meta.i18n ?? {};
		}

		await tick();
		savedDraft = JSON.stringify(modelInfo);
	};
	const productionHandler = async (value: any) => {
		await loadModel(value);
		try {
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections
						? ($settings?.directConnections ?? null)
						: null
				)
			);
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	onMount(async () => {
		languages = await getLanguages();
		await tools.set((await getTools(localStorage.token).catch(() => null)) ?? []);
		skillsList = (await getSkills(localStorage.token).catch(() => null)) ?? [];
		if (!$functions) {
			await functions.set(await getFunctions(localStorage.token));
		}
		if (suggestionTags.length === 0) {
			await loadSuggestionTags();
		}
		if (voices.length === 0) {
			await loadVoices();
		}

		// Fetch admin-configured default model metadata so the editor
		// reflects the actual defaults rather than hardcoded values
		const modelsConfig = await getModelsDefaults(localStorage.token).catch(() => null);
		defaultMeta = modelsConfig?.DEFAULT_MODEL_METADATA ?? {};

		// Use admin defaults as base, falling back to hardcoded defaults
		capabilities = { ...DEFAULT_CAPABILITIES, ...(defaultMeta.capabilities ?? {}) };
		defaultFeatureIds = defaultMeta.defaultFeatureIds ?? [];
		builtinTools = defaultMeta.builtinTools ?? {};

		// Scroll to top 'workspace-container' element
		const workspaceContainer = document.getElementById('workspace-container');
		if (workspaceContainer) {
			workspaceContainer.scrollTop = 0;
		}

		await loadModel(model);
		loaded = true;
	});
</script>

{#if loaded}
	<input
		bind:this={backgroundInput}
		type="file"
		accept="image/png,image/jpeg,image/webp,image/gif"
		hidden
		on:change={async () => {
			const selected = backgroundInput.files?.[0];
			backgroundInput.value = '';
			if (!selected || readOnly || loading) return;
			loading = true;
			const candidate = URL.createObjectURL(selected);
			try {
				if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(selected.type)) {
					throw new Error($i18n.t('Background image must be PNG, JPEG, WebP, or GIF.'));
				}
				if (selected.size > 5 * 1024 * 1024)
					throw new Error($i18n.t('Background image must be at most 5 MiB.'));
				const image = new Image();
				image.src = candidate;
				await image.decode();
				if (image.naturalWidth * image.naturalHeight > 25_000_000) {
					throw new Error($i18n.t('Background image must be at most 25 megapixels.'));
				}
				clearBackgroundPreview();
				backgroundPreview = candidate;
				backgroundFile = selected;
			} catch (error) {
				URL.revokeObjectURL(candidate);
				toast.error(error instanceof Error ? error.message : $i18n.t('Invalid background image.'));
			} finally {
				loading = false;
			}
		}}
	/>
	<ConfirmDialog
		bind:show={showDiscard}
		title={$i18n.t('Discard unsaved changes?')}
		message={$i18n.t('Your unsaved changes will be lost.')}
		on:confirm={() => {
			allowNavigation = true;
			afterDiscard?.();
		}}
	/>
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessGrants
		accessRoles={preset ? ['read', 'write'] : ['read']}
		share={$user?.permissions?.sharing?.models || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
		shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
		allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) ||
			$user?.role === 'admin'}
	/>

	<div class="flex h-full min-h-0 w-full flex-col">
		<div class="flex shrink-0 items-center gap-3" class:px-3={!admin}>
			{#if onBack}
				<button
					class="flex h-6 w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
					type="button"
					on:click={() => {
						discardThen(() => {
							allowNavigation = true;
							onBack?.();
						});
					}}
				>
					<ChevronLeft className="size-3" strokeWidth="2" />
					<span>{$i18n.t('Back')}</span>
				</button>
			{/if}
			{#if edit && model?.version_id && !readOnly}
				<ModelHistory
					bind:this={historyMenu}
					{model}
					{dirty}
					bind:selected={selectedVersion}
					bind:selecting={selectingVersion}
					bind:promoting={promotingVersion}
					onProduction={productionHandler}
				/>
			{/if}
			{#if !historical && !readOnly}
				<div class="ms-auto flex shrink-0 items-center gap-1 pr-0.5">
					<LanguageModeSelect
						bind:value={editingLocale}
						{languages}
						{translatedLocales}
						className="w-fit"
					/>
					<AccessButton on:click={() => (showAccessControlModal = true)} />
				</div>
			{/if}
		</div>

		{#if selectingVersion}
			<div class="flex flex-1 justify-center py-8"><Spinner className="size-5" /></div>
		{:else if selectedVersion}
			<section aria-label={$i18n.t('Model version preview')} class="min-h-0 flex-1">
				{#key selectedVersion.id}
					<svelte:self
						model={{ id: model.id, ...selectedVersion.snapshot }}
						edit
						readOnly
						{admin}
						preset={!!selectedVersion.snapshot.base_model_id}
					/>
				{/key}
			</section>
			<div class="flex shrink-0 justify-end py-2" class:px-1={admin} class:px-3={!admin}>
				<button
					type="button"
					class="flex h-7 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					disabled={promotingVersion}
					on:click={() => historyMenu.requestPromotion()}
				>
					{$i18n.t('Set as Production')}
				</button>
			</div>
		{/if}
		<div
			class:hidden={historical}
			class="min-h-0 w-full flex-1 overflow-y-auto px-1 scrollbar-hover"
		>
			<input
				bind:this={filesInputElement}
				bind:files={inputFiles}
				type="file"
				hidden
				accept="image/*"
				on:change={() => {
					let reader = new FileReader();
					reader.onload = (event) => {
						let originalImageUrl = `${event.target?.result}`;

						// For animated formats (gif, webp), skip resizing to preserve animation
						const fileType = (inputFiles[0] as any)?.['type'];
						if (fileType === 'image/gif' || fileType === 'image/webp') {
							info.meta.profile_image_url = originalImageUrl;
							inputFiles = null;
							filesInputElement.value = '';
							return;
						}

						const img = new Image();
						img.src = originalImageUrl;

						img.onload = function () {
							const canvas = document.createElement('canvas');
							const ctx = canvas.getContext('2d');

							// Calculate the aspect ratio of the image
							const aspectRatio = img.width / img.height;

							// Calculate the new width and height to fit within 100x100
							let newWidth, newHeight;
							if (aspectRatio > 1) {
								newWidth = 250 * aspectRatio;
								newHeight = 250;
							} else {
								newWidth = 250;
								newHeight = 250 / aspectRatio;
							}

							// Set the canvas size
							canvas.width = 250;
							canvas.height = 250;

							// Calculate the position to center the image
							const offsetX = (250 - newWidth) / 2;
							const offsetY = (250 - newHeight) / 2;

							// Draw the image on the canvas
							ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

							// Get the base64 representation of the compressed image
							const compressedSrc = canvas.toDataURL('image/webp', 0.8);

							// Display the compressed image
							info.meta.profile_image_url = compressedSrc;

							inputFiles = null;
							filesInputElement.value = '';
						};
					};

					if (
						inputFiles &&
						inputFiles.length > 0 &&
						['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
							(inputFiles[0] as any)?.['type']
						)
					) {
						reader.readAsDataURL(inputFiles[0]);
					} else {
						console.log(`Unsupported File Type '${(inputFiles[0] as any)?.['type']}'.`);
						inputFiles = null;
					}
				}}
			/>

			{#if !edit || (edit && model)}
				<!-- svelte-ignore a11y_no_noninteractive_element_interactions (Capture listeners block changes from custom controls in read-only fieldsets.) -->
				<form
					id={formId}
					class="flex w-full flex-col gap-2.5 md:flex-row"
					on:click|capture={preventReadOnlyEdit}
					on:keydown|capture={preventReadOnlyEdit}
					on:pointerdown|capture={preventReadOnlyEdit}
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="w-full px-1">
						<fieldset disabled={readOnly} class="flex min-w-0 w-full flex-col gap-3">
							<div class="group/header flex min-w-0 flex-col gap-3">
								<div
									class="relative mt-2 w-full transition-[height] duration-200 motion-reduce:transition-none {backgroundPreview ||
									info.meta.background_image_url
										? 'h-36 sm:h-48'
										: 'h-20'}"
								>
									{#if backgroundPreview || info.meta.background_image_url}
										<img
											src={backgroundPreview ?? info.meta.background_image_url}
											alt={$i18n.t('Background image preview')}
											class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full rounded-xl object-cover"
										/>
									{:else}
										<div
											aria-hidden="true"
											class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full rounded-xl bg-gray-100 dark:bg-gray-850"
										></div>
									{/if}
								</div>

								<div class="flex w-full min-w-0 items-center gap-3 py-0.5">
									<div
										class="relative flex min-w-0 flex-1 items-center gap-3.5 px-3 md:px-5 pb-1 {backgroundPreview ||
										info.meta.background_image_url
											? '-mt-14 sm:-mt-16'
											: '-mt-9'}"
									>
										<!-- LICENSE covers this Open WebUI fallback logo.
									Do not alter, remove, obscure, or replace it except as LICENSE permits:
									https://docs.openwebui.com/license. -->
										<div class="group relative size-12 shrink-0">
											<button
												class="group relative flex size-full items-center overflow-hidden rounded-xl {info
													.meta.profile_image_url !== `${WEBUI_BASE_URL}/static/favicon.png`
													? 'bg-transparent'
													: 'bg-gray-50 dark:bg-gray-850'} ring-1 ring-gray-200/70 transition hover:ring-gray-300 dark:ring-white/10 dark:hover:ring-white/20"
												type="button"
												aria-label={$i18n.t('Upload profile image')}
												on:click={() => {
													filesInputElement.click();
												}}
											>
												{#if info.meta.profile_image_url}
													<img
														src={info.meta.profile_image_url}
														alt={$i18n.t('model profile')}
														class="size-full object-cover"
													/>
												{:else}
													<img
														src="{WEBUI_BASE_URL}/static/favicon.png"
														alt={$i18n.t('model profile')}
														class="size-full object-cover"
													/>
												{/if}

												<div
													class="absolute bottom-0 right-0 z-10 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100"
												>
													<div class="m-1">
														<div
															class="rounded-full bg-gray-900 p-1 text-white shadow-sm transition dark:bg-white dark:text-black"
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="size-3"
															>
																<path
																	fill-rule="evenodd"
																	d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
																	clip-rule="evenodd"
																/>
															</svg>
														</div>
													</div>
												</div>

												<div
													class="absolute inset-0 bg-white opacity-0 transition group-hover:opacity-20 dark:bg-black"
												></div>
											</button>

											{#if info.meta.profile_image_url && info.meta.profile_image_url !== `${WEBUI_BASE_URL}/static/favicon.png`}
												<button
													class="absolute left-1/2 top-full mt-1 -translate-x-1/2 text-[0.5rem] leading-none text-gray-400 opacity-0 transition group-hover:opacity-60 hover:text-gray-500 hover:opacity-100 group-focus-within:opacity-60 dark:text-gray-600 dark:hover:text-gray-400"
													on:click={() => {
														info.meta.profile_image_url = `${WEBUI_BASE_URL}/static/favicon.png`;
													}}
													type="button"
												>
													{$i18n.t('Reset')}</button
												>
											{/if}
										</div>

										<div class="min-w-0 w-full flex-1">
											<div class="flex min-w-0 items-center gap-2">
												{#if editingLocale}
													<input
														class="min-w-0 flex-1 bg-transparent text-base leading-tight text-gray-900 outline-hidden placeholder:text-gray-300 dark:text-white dark:placeholder:text-gray-700 md:text-lg"
														placeholder={name || $i18n.t('Model Name')}
														value={localizedField('name')}
														on:input={(e) =>
															setLocalizedField(
																'name',
																(e.currentTarget as HTMLInputElement).value
															)}
													/>
												{:else}
													<input
														class="min-w-0 flex-1 bg-transparent text-base leading-tight text-gray-900 outline-hidden placeholder:text-gray-300 dark:text-white dark:placeholder:text-gray-700 md:text-lg"
														placeholder={$i18n.t('Model Name')}
														bind:value={name}
														required
													/>
												{/if}
												{#if !readOnly}
													<div
														class="[@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover/header:opacity-100 [@media(hover:hover)]:group-focus-within/header:opacity-100 absolute bottom-full right-3 mb-1 md:static md:mb-0 flex shrink-0 items-center gap-1 text-xs"
													>
														{#if loading}<Spinner />{/if}
														<!-- Previous labels retained for i18n extraction: {$i18n.t('Background Image')} -->
														{#if backgroundPreview || info.meta.background_image_url}
															<button
																type="button"
																class="rounded-md px-1 py-1 text-xs font-normal text-gray-500 transition hover:text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-300"
																disabled={loading}
																title={$i18n.t(
																	'PNG, JPEG, WebP, or GIF. Up to 5 MiB and 25 megapixels.'
																)}
																on:click={() => backgroundInput.click()}>{$i18n.t('Change')}</button
															>
															<button
																type="button"
																class="rounded-md px-1 py-1 text-xs font-normal text-gray-500 transition hover:text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-300"
																disabled={loading}
																on:click={() => {
																	clearBackgroundPreview();
																	backgroundFile = null;
																	info.meta.background_image_url = null;
																}}>{$i18n.t('Remove')}</button
															>
														{:else}
															<button
																type="button"
																class="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-gray-500 transition hover:text-gray-700 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-300"
																disabled={loading}
																title={$i18n.t(
																	'PNG, JPEG, WebP, or GIF. Up to 5 MiB and 25 megapixels.'
																)}
																on:click={() => backgroundInput.click()}
															>
																<Photo />
																{$i18n.t('Add background')}
															</button>
														{/if}
													</div>
												{/if}
											</div>

											{#if editingLocale}
												<div class="mt-1 flex items-center justify-end gap-3 text-[0.6875rem]">
													<div
														class="flex shrink-0 items-center gap-2 text-gray-500 dark:text-gray-400"
													>
														<button type="button" on:click={() => setLocalizedField('name', name)}>
															{$i18n.t('Copy default')}
														</button>
														{#if localizedField('name')}
															<button type="button" on:click={() => clearLocalizedField('name')}>
																{$i18n.t('Use default')}
															</button>
														{/if}
													</div>
												</div>
											{/if}

											<input
												class="block w-full bg-transparent py-0.5 text-xs text-gray-500 outline-hidden placeholder:text-gray-300 dark:text-gray-500 dark:placeholder:text-gray-700"
												placeholder={$i18n.t('Model ID')}
												bind:value={id}
												disabled={edit}
												required
											/>
										</div>
									</div>
								</div>
							</div>
							<div class="flex min-w-0 flex-col gap-3 px-3 md:px-5">
								<div>
									<div class="mb-1 flex w-full items-center justify-between">
										{#if editingLocale}
											<div class="self-center text-xs font-normal text-gray-600 dark:text-gray-400">
												{$i18n.t('Description ({{language}})', {
													language: editingLocaleLabel || editingLocale
												})}
											</div>
											<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
												<button
													type="button"
													on:click={() =>
														setLocalizedField('description', info.meta.description ?? '')}
												>
													{$i18n.t('Copy default')}
												</button>
												{#if localizedField('description')}
													<button type="button" on:click={() => clearLocalizedField('description')}>
														{$i18n.t('Use default')}
													</button>
												{/if}
											</div>
										{:else}
											<button
												class="grid w-full grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 rounded-sm text-start text-xs font-normal text-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 sm:grid-cols-[8rem_minmax(0,1fr)]"
												type="button"
												aria-pressed={enableDescription ? 'true' : 'false'}
												aria-label={enableDescription
													? $i18n.t('Custom description enabled')
													: $i18n.t('Default description enabled')}
												on:click={() => {
													enableDescription = !enableDescription;
												}}
											>
												<span class="font-normal text-gray-600 dark:text-gray-400">
													{$i18n.t('Description')}
												</span>
												{#if !enableDescription}
													<span class="justify-self-end">{$i18n.t('Default')}</span>
												{:else}
													<span class="justify-self-end">{$i18n.t('Custom')}</span>
												{/if}
											</button>
										{/if}
									</div>

									{#if editingLocale}
										<Textarea
											className="w-full resize-none overflow-y-hidden bg-transparent py-1 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 font-normal text-gray-900 dark:text-gray-100"
											placeholder={info.meta.description ||
												$i18n.t('Add a short description about what this model does')}
											minSize={32}
											value={localizedField('description')}
											onInput={(e) =>
												setLocalizedField(
													'description',
													(e.currentTarget as HTMLTextAreaElement).value
												)}
										/>
									{:else if enableDescription}
										<Textarea
											className="w-full resize-none overflow-y-hidden bg-transparent py-1 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 font-normal text-gray-900 dark:text-gray-100"
											placeholder={$i18n.t('Add a short description about what this model does')}
											minSize={32}
											bind:value={info.meta.description}
										/>
									{/if}
								</div>

								<div class="flex min-w-0 flex-col gap-2">
									{#if preset}
										<div
											class="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 sm:grid-cols-[8rem_minmax(0,1fr)]"
										>
											<div class="text-xs font-normal text-gray-600 dark:text-gray-400">
												<ModelSettingsLabel
													label={$i18n.t('Base Model (From)')}
													description={$i18n.t(
														'Choose the underlying model that generates responses for this custom model.'
													)}
												/>
											</div>

											<div class="min-w-0">
												<ModelSelector
													id="workspace-base-model"
													placeholder={$i18n.t('Select a base model')}
													searchPlaceholder={$i18n.t('Search a model')}
													items={getBaseModelItems($models)}
													triggerClassName="text-xs font-normal text-gray-900 dark:text-gray-100"
													selectionOnly
													includeHidden={$user?.role === 'admin'}
													bind:value={info.base_model_id}
												/>
											</div>
										</div>
									{/if}

									<div
										class="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 sm:grid-cols-[8rem_minmax(0,1fr)]"
									>
										<div class="pt-1 text-xs font-normal text-gray-600 dark:text-gray-400">
											<ModelSettingsLabel
												label={$i18n.t('Tags')}
												description={$i18n.t(
													'Add tags to organize models and make them easier to find.'
												)}
											/>
										</div>
										<div class="min-w-0">
											<Tags
												tags={info?.meta?.tags ?? []}
												{suggestionTags}
												on:delete={(e) => {
													const tagName = e.detail;
													info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
												}}
												on:add={(e) => {
													const tagName = e.detail;
													if (!(info?.meta?.tags ?? null)) {
														info.meta.tags = [{ name: tagName }];
													} else {
														info.meta.tags = [...info.meta.tags, { name: tagName }];
													}
												}}
											/>
										</div>
									</div>
								</div>
							</div>
						</fieldset>

						<div class="px-2.5 md:px-4">
							<section class="mt-4">
								<div class="space-y-2 px-1">
									<div class="text-xs font-normal text-gray-600 dark:text-gray-400">
										<ModelSettingsLabel
											label={$i18n.t('System Prompt')}
											description={$i18n.t(
												'Set instructions that guide how this model behaves throughout a chat.'
											)}
										/>
									</div>

									{#if showSystemPrompt || !system.trim()}
										<fieldset disabled={readOnly} class="min-w-0">
											<div>
												<Textarea
													className="min-h-12 w-full resize-none overflow-y-hidden bg-transparent py-1 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 font-normal text-gray-900 dark:text-gray-100"
													placeholder={$i18n.t(
														'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
													)}
													rows={2}
													minSize={48}
													bind:value={system}
												/>
											</div>
											{#if chatVariablesPreview.fields.length > 0 || chatVariablesPreview.userFields.length > 0 || chatVariablesPreview.warnings.length > 0}
												<div class="mt-2 border-t border-gray-100/60 pt-2 dark:border-gray-850/60">
													<div class="mb-1.5 flex items-center justify-between gap-2">
														<div class="text-xs font-normal text-gray-600 dark:text-gray-400">
															{$i18n.t('Detected Variables')}
														</div>
														{#if chatVariablesPreview.fields.length + chatVariablesPreview.userFields.length > 0}
															<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
																{chatVariablesPreview.fields.length +
																	chatVariablesPreview.userFields.length}
															</div>
														{/if}
													</div>

													{#if chatVariablesPreview.fields.length > 0}
														<div
															class="mb-1 text-[0.6875rem] font-normal text-gray-600 dark:text-gray-400"
														>
															{$i18n.t('Chat Variables')}
														</div>
														<div class="flex flex-wrap gap-x-3 gap-y-1.5 text-xs">
															{#each chatVariablesPreview.fields as field}
																<div
																	class="flex items-center gap-1 font-normal text-gray-900 dark:text-gray-100"
																>
																	<span class="font-medium">{field.key}</span>
																	<span class="text-gray-400 dark:text-gray-600">{field.type}</span>
																	{#if field.required}
																		<span class="text-amber-600 dark:text-amber-400">required</span>
																	{/if}
																</div>
															{/each}
														</div>
													{/if}

													{#if chatVariablesPreview.userFields.length > 0}
														<div
															class="mb-1 mt-2 text-[0.6875rem] font-normal text-gray-600 dark:text-gray-400"
														>
															{$i18n.t('User Variables')}
														</div>
														<div class="flex flex-wrap gap-x-3 gap-y-1.5 text-xs">
															{#each chatVariablesPreview.userFields as field}
																<div
																	class="flex items-center gap-1 font-normal text-gray-900 dark:text-gray-100"
																>
																	<span class="font-medium">{field.key}</span>
																</div>
															{/each}
														</div>
													{/if}

													{#if chatVariablesPreview.warnings.length > 0}
														<div
															class="mt-2 flex flex-col gap-1 text-xs text-amber-600 dark:text-amber-400"
														>
															{#each chatVariablesPreview.warnings as warning}
																<div>{warning}</div>
															{/each}
														</div>
													{/if}
												</div>
											{/if}
										</fieldset>
									{:else}
										<button
											type="button"
											aria-label={$i18n.t('System Prompt')}
											aria-expanded={false}
											on:click={() => {
												showSystemPrompt = true;
											}}
											class="w-full cursor-text text-start line-clamp-5 whitespace-pre-wrap break-words text-[0.8125rem] font-normal text-gray-900 dark:text-gray-100"
										>
											{system}
										</button>
									{/if}
									{#if system.trim()}
										<button
											class="block text-xs text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
											type="button"
											aria-expanded={showSystemPrompt}
											on:click={() => {
												showSystemPrompt = !showSystemPrompt;
											}}
										>
											{showSystemPrompt ? $i18n.t('Show less') : $i18n.t('Show more')}
										</button>
									{/if}
								</div>
								<!-- Previous labels retained for i18n extraction: {$i18n.t('Model Params')} -->
								<div class="mt-2 space-y-0.5">
									<button
										type="button"
										class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-start text-xs font-normal focus-visible:outline focus-visible:outline-2 sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
										aria-expanded={showAdvanced}
										on:click={() => (showAdvanced = !showAdvanced)}
									>
										<span class="font-normal text-gray-600 dark:text-gray-400"
											><ModelSettingsLabel
												label={$i18n.t('Advanced Params')}
												description={$i18n.t(
													'Override generation settings such as temperature, token limits, and sampling. Unmodified settings use the provider defaults.'
												)}
											/></span
										>
										<span class="text-gray-900 dark:text-gray-100">
											<!-- Previous non-plural key retained for i18n extraction: {$i18n.t('{{count}} modified')} -->
											{modifiedParamCount
												? $i18n.t('{{count}} modified', { count: modifiedParamCount })
												: $i18n.t('Default')}
										</span>
										<ChevronRight
											className={`size-3 text-gray-400 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
										/>
									</button>

									{#if showAdvanced}
										<fieldset disabled={readOnly} class="min-w-0 my-2 pl-3">
											<AdvancedParams admin={true} custom={true} layout="grid" bind:params />
										</fieldset>
									{/if}
									<fieldset disabled={readOnly} class="min-w-0">
										{#if !editingLocale}
											<ModelControls bind:controls={params.model_controls} />
										{:else if Object.keys(params.model_controls ?? {}).length}
											<div class="flex h-7 items-center text-xs text-gray-600 dark:text-gray-400">
												{$i18n.t('Model controls')}
											</div>
											<TranslationTable
												value={controlTranslations}
												source={modelControlTranslationSource(params.model_controls)}
												filename={`model-${id}-${editingLocale}.json`}
												onChange={setControlTranslations}
											/>
										{/if}
									</fieldset>
								</div>
							</section>

							<fieldset disabled={readOnly} class="min-w-0">
								<section class="mt-0.5">
									<ModelSettingsSection
										label={$i18n.t('Prompts')}
										description={$i18n.t(
											'Set the starter suggestions people see when opening a new chat with this model.'
										)}
										summary={editingLocale
											? Array.isArray(info.meta.i18n?.[editingLocale]?.suggestion_prompts)
												? $i18n.t('Custom')
												: $i18n.t('Default')
											: info.meta.suggestion_prompts == null
												? $i18n.t('Default')
												: `${$i18n.t('Custom')} · ${info.meta.suggestion_prompts.length}`}
									>
										{#if editingLocale}
											<LocalizedPromptSuggestions
												promptSuggestions={info.meta.suggestion_prompts ?? []}
												bind:localizedPromptSuggestions={info.meta.i18n}
												locale={editingLocale}
												localeLabel={editingLocaleLabel}
												disabled={readOnly}
											/>
										{:else if info.meta.suggestion_prompts != null}
											<PromptSuggestions
												bind:promptSuggestions={info.meta.suggestion_prompts}
												disabled={readOnly}
											>
												<button
													slot="label"
													disabled={readOnly}
													type="button"
													class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
													on:click={() => {
														customPromptDraft = structuredClone(info.meta.suggestion_prompts);
														info.meta.suggestion_prompts = null;
													}}>{$i18n.t('Use default')}</button
												>
											</PromptSuggestions>
										{:else}
											<div
												class="flex items-center justify-between gap-3 px-1 py-1 text-xs text-gray-500 dark:text-gray-400"
											>
												<span>{$i18n.t('Using default prompt suggestions')}</span>
												<button
													type="button"
													class="shrink-0 hover:text-gray-900 dark:hover:text-gray-100"
													on:click={() => {
														info.meta.suggestion_prompts = customPromptDraft ?? [
															{ content: '', title: ['', ''] }
														];
													}}>{$i18n.t('Customize')}</button
												>
											</div>
										{/if}
									</ModelSettingsSection>
								</section>

								<hr class="my-3 border-gray-100/60 dark:border-gray-850/60" />

								<div class="my-3 space-y-0.5">
									<Knowledge bind:selectedItems={knowledge} disabled={readOnly} />
									<ToolsSelector
										bind:selectedToolIds={toolIds}
										tools={$tools ?? []}
										disabled={readOnly}
									/>
									<SkillsSelector
										bind:selectedSkillIds={skillIds}
										skills={skillsList}
										disabled={readOnly}
									/>
									{#if ($functions ?? []).some((func) => func.type === 'filter')}
										<FiltersSelector
											bind:selectedFilterIds={filterIds}
											bind:defaultFilterIds
											filters={($functions ?? []).filter((func) => func.type === 'filter')}
											disabled={readOnly}
										/>
									{/if}
									{#if ($functions ?? []).some((func) => func.type === 'action')}
										<ActionsSelector
											bind:selectedActionIds={actionIds}
											actions={($functions ?? []).filter((func) => func.type === 'action')}
											disabled={readOnly}
										/>
									{/if}
								</div>
								<div class="space-y-0.5">
									<Capabilities
										bind:capabilities
										bind:defaultFeatureIds
										bind:builtinTools
										disabled={readOnly}
									/>
									<ModelSettingsSection
										label={$i18n.t('Voice')}
										description={$i18n.t(
											'Configure the realtime voice, voice avatar, and text-to-speech voice for this model.'
										)}
										summary={[
											$config?.audio?.realtime?.enabled
												? voice.voice || $i18n.t('Admin default')
												: null,
											$config?.audio?.realtime?.enabled || voiceAvatar
												? voiceAvatar
													? $i18n.t('Custom avatar')
													: $i18n.t('Default orb')
												: null,
											tts.voice
										]
											.filter(Boolean)
											.join(' · ') || $i18n.t('Default')}
									>
										{#if $config?.audio?.realtime?.enabled}
											<div
												class="grid min-h-8 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 text-xs sm:grid-cols-[8rem_minmax(0,1fr)]"
											>
												<div class="flex min-w-0 items-center">
													<label
														for="realtime-voice-input"
														class="self-center text-xs font-normal text-gray-600 dark:text-gray-400"
													>
														{$i18n.t('Realtime Voice')}
													</label>
												</div>
												<TTSVoiceInput
													className="w-full font-normal text-gray-900 dark:text-gray-100"
													id="realtime-voice"
													bind:value={voice.voice}
													placeholder={$i18n.t('Admin default')}
												/>
											</div>
										{/if}
										{#if $config?.audio?.realtime?.enabled || voiceAvatar}
											<VoiceAvatarSettings
												bind:value={voiceAvatar}
												bind:file={avatarFile}
												bind:animationFiles
												disabled={loading || readOnly}
											/>
										{/if}
										<div
											class="grid min-h-8 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 text-xs sm:grid-cols-[8rem_minmax(0,1fr)]"
										>
											<div class="flex min-w-0 items-center">
												<div
													class="self-center text-xs font-normal text-gray-600 dark:text-gray-400"
												>
													{$i18n.t('TTS Voice')}
												</div>
											</div>
											<TTSVoiceInput
												className="w-full font-normal text-gray-900 dark:text-gray-100"
												bind:value={tts.voice}
												{voices}
												placeholder={$i18n.t('e.g. alloy, echo, shimmer')}
											/>
										</div>
									</ModelSettingsSection>
									{#if capabilities.terminal}
										<TerminalSelector bind:terminalId />
									{/if}
								</div>
							</fieldset>

							<div class="my-2 text-xs text-gray-400 dark:text-gray-500">
								<div
									class="flex w-full items-center gap-2 opacity-30 transition-opacity hover:opacity-60 focus-within:opacity-60"
								>
									<button
										type="button"
										class="flex h-7 min-w-0 flex-1 items-center justify-between gap-3 rounded-sm text-start text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
										aria-expanded={showPreview}
										on:click={() => (showPreview = !showPreview)}
									>
										<span class="font-normal">{$i18n.t('JSON Preview')}</span>
										<span aria-hidden="true">{showPreview ? $i18n.t('Hide') : $i18n.t('Show')}</span
										>
									</button>
									<button
										class="px-1.5 py-0.5 text-xs flex rounded-sm"
										type="button"
										on:click={async () => {
											const copied = await copyToClipboard(
												JSON.stringify(readOnly ? model : modelInfo, null, 2)
											);
											if (copied) {
												toast.success($i18n.t('Copied to clipboard'));
											}
										}}
									>
										{$i18n.t('Copy')}
									</button>
								</div>
								{#if showPreview}
									<div class="pt-2">
										<textarea
											class="w-full bg-transparent text-xs leading-5 outline-hidden resize-none font-normal text-gray-900 dark:text-gray-100"
											rows="8"
											value={JSON.stringify(readOnly ? model : modelInfo, null, 2)}
											disabled
											readonly
										/>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</form>
			{/if}
		</div>
		{#if !readOnly && !historical && (!edit || model)}
			<div
				class="flex shrink-0 items-center justify-end gap-2 py-2"
				class:px-1={admin}
				class:px-3={!admin}
			>
				{#if edit}
					<input
						form={formId}
						type="text"
						aria-label={$i18n.t('Commit message')}
						placeholder={$i18n.t('Describe this change')}
						class="min-w-0 flex-1 border-0 bg-transparent px-1 text-xs outline-hidden focus:ring-0"
						bind:value={commitMessage}
					/>
				{/if}
				<button
					form={formId}
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					type="submit"
					disabled={loading || (edit && !configurationChanged)}
				>
					{edit ? $i18n.t('Save & Update') : $i18n.t('Save & Create')}
					{#if loading}<Spinner className="size-3" />{/if}
				</button>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex h-full w-full items-center justify-center" role="status">
		<Spinner className="size-5" />
		<span class="sr-only">{$i18n.t('Loading...')}</span>
	</div>
{/if}
