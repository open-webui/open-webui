<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import ModelSettingsSection from '$lib/components/workspace/Models/ModelSettingsSection.svelte';
	import ModelSettingToggle from '$lib/components/workspace/Models/ModelSettingToggle.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let hiddenInterfaceElements: string[] = [];

	let groups;
	$: groups = [
		{
			label: $i18n.t('settings.admin.models.defaults.modelCapabilities.label'),
			elements: [
				{
					id: 'model_editor.capability.vision',
					label: $i18n.t('settings.admin.models.capabilities.vision.label')
				},
				{
					id: 'model_editor.capability.file_upload',
					label: $i18n.t('settings.admin.models.capabilities.fileUpload.label')
				},
				{
					id: 'model_editor.capability.file_context',
					label: $i18n.t('settings.admin.models.capabilities.fileContext.label')
				},
				{
					id: 'model_editor.capability.web_search',
					label: $i18n.t('settings.admin.models.capabilities.webSearch.label')
				},
				{
					id: 'model_editor.capability.image_generation',
					label: $i18n.t('settings.admin.models.capabilities.imageGeneration.label')
				},
				{
					id: 'model_editor.capability.code_interpreter',
					label: $i18n.t('settings.admin.models.capabilities.codeInterpreter.label')
				},
				{
					id: 'model_editor.capability.terminal',
					label: $i18n.t('settings.admin.models.capabilities.terminal.label')
				},
				{
					id: 'model_editor.capability.usage',
					label: $i18n.t('settings.admin.models.capabilities.usage.label')
				},
				{
					id: 'model_editor.capability.citations',
					label: $i18n.t('settings.admin.models.capabilities.citations.label')
				},
				{
					id: 'model_editor.capability.status_updates',
					label: $i18n.t('settings.admin.models.capabilities.statusUpdates.label')
				},
				{
					id: 'model_editor.capability.memory',
					label: $i18n.t('settings.admin.models.capabilities.memory.label')
				},
				{
					id: 'model_editor.capability.builtin_tools',
					label: $i18n.t('settings.admin.models.capabilities.builtinTools.label')
				}
			]
		},
		{
			label: $i18n.t('settings.admin.models.defaultFeatures.title'),
			elements: [
				{
					id: 'model_editor.default_feature.web_search',
					label: $i18n.t('settings.admin.models.capabilities.webSearch.label')
				},
				{
					id: 'model_editor.default_feature.image_generation',
					label: $i18n.t('settings.admin.models.capabilities.imageGeneration.label')
				},
				{
					id: 'model_editor.default_feature.code_interpreter',
					label: $i18n.t('settings.admin.models.capabilities.codeInterpreter.label')
				}
			]
		},
		{
			label: $i18n.t('settings.admin.models.builtinTools.title'),
			elements: [
				{
					id: 'model_editor.builtin_tool.time',
					label: $i18n.t('settings.admin.models.builtinTools.time.label')
				},
				{
					id: 'model_editor.builtin_tool.user_input',
					label: $i18n.t('settings.admin.models.builtinTools.userInput.label')
				},
				{
					id: 'model_editor.builtin_tool.memory',
					label: $i18n.t('settings.admin.models.builtinTools.memory.label')
				},
				{
					id: 'model_editor.builtin_tool.chats',
					label: $i18n.t('settings.admin.models.builtinTools.chats.label')
				},
				{
					id: 'model_editor.builtin_tool.notes',
					label: $i18n.t('settings.admin.models.builtinTools.notes.label')
				},
				{
					id: 'model_editor.builtin_tool.knowledge',
					label: $i18n.t('settings.admin.models.builtinTools.knowledge.label')
				},
				{
					id: 'model_editor.builtin_tool.files',
					label: $i18n.t('settings.admin.models.builtinTools.files.label')
				},
				{
					id: 'model_editor.builtin_tool.channels',
					label: $i18n.t('settings.admin.models.builtinTools.channels.label')
				},
				{
					id: 'model_editor.builtin_tool.notifications',
					label: $i18n.t('settings.admin.models.builtinTools.notifications.label')
				},
				{
					id: 'model_editor.builtin_tool.web_search',
					label: $i18n.t('settings.admin.models.builtinTools.webSearch.label')
				},
				{
					id: 'model_editor.builtin_tool.image_generation',
					label: $i18n.t('settings.admin.models.builtinTools.imageGeneration.label')
				},
				{
					id: 'model_editor.builtin_tool.code_interpreter',
					label: $i18n.t('settings.admin.models.builtinTools.codeInterpreter.label')
				},
				{
					id: 'model_editor.builtin_tool.tasks',
					label: $i18n.t('settings.admin.models.builtinTools.tasks.label')
				},
				{
					id: 'model_editor.builtin_tool.automations',
					label: $i18n.t('settings.admin.models.builtinTools.automations.label')
				},
				{
					id: 'model_editor.builtin_tool.calendar',
					label: $i18n.t('settings.admin.models.builtinTools.calendar.label')
				},
				{
					id: 'model_editor.builtin_tool.subagents',
					label: $i18n.t('settings.admin.models.builtinTools.subagents.label')
				},
				{
					id: 'model_editor.builtin_tool.skills',
					label: $i18n.t('settings.admin.models.builtinTools.skills.label')
				}
			]
		},
		{
			label: $i18n.t('Input Menu'),
			elements: [
				{ id: 'input_menu.capture', label: $i18n.t('Capture') },
				{ id: 'input_menu.compare_text', label: $i18n.t('Compare text') },
				{ id: 'input_menu.attach_webpage', label: $i18n.t('Attach Webpage') },
				{ id: 'input_menu.attach_files', label: $i18n.t('Attach Files') },
				{ id: 'input_menu.attach_notes', label: $i18n.t('Attach Notes') },
				{ id: 'input_menu.attach_knowledge', label: $i18n.t('Attach Knowledge') },
				{ id: 'input_menu.reference_chats', label: $i18n.t('Reference Chats') }
			]
		},
		{
			label: $i18n.t('Slash Commands'),
			elements: [
				{ id: 'command.status', label: '/status' },
				{ id: 'command.model', label: '/model' },
				{ id: 'command.compare', label: '/compare' },
				{ id: 'command.settings', label: '/settings' }
			]
		},
		{
			label: $i18n.t('Response Actions'),
			elements: [
				{ id: 'response.usage', label: $i18n.t('settings.admin.models.capabilities.usage.label') },
				{ id: 'response.merge', label: $i18n.t('Merge Responses') },
				{ id: 'response.code_preview', label: $i18n.t('Preview') },
				{ id: 'response.fork', label: $i18n.t('Fork chat') }
			]
		},
		{
			label: $i18n.t('Chat Menu'),
			elements: [
				{ id: 'chat_menu.artifacts', label: $i18n.t('Artifacts') },
				{ id: 'chat_menu.archive', label: $i18n.t('Archive') },
				{ id: 'chat_menu.tags', label: $i18n.t('Tags') }
			]
		},
		{
			label: $i18n.t('Model Selector'),
			elements: [
				{ id: 'model_selector.set_default', label: $i18n.t('Set as default') },
				{ id: 'model_selector.keep_in_sidebar', label: $i18n.t('Keep in Sidebar') }
			]
		},
		{
			label: $i18n.t('Settings'),
			elements: [
				{ id: 'settings.usage', label: $i18n.t('settings.personal.usage.title') },
				{
					id: 'settings.stt_web_api',
					label: `${$i18n.t('settings.personal.audio.speechToTextEngine.label')}: ${$i18n.t('Web API')}`
				},
				{
					id: 'settings.tts_kokoro',
					label: `${$i18n.t('settings.personal.audio.textToSpeechEngine.label')}: ${$i18n.t('Kokoro.js (Browser)')}`
				}
			]
		},
		{
			label: $i18n.t('settings.personal.interface.title'),
			elements: [
				{
					id: 'settings.interface.user_location',
					label: $i18n.t('settings.personal.interface.allowUserLocation.label')
				},
				{
					id: 'settings.interface.chat_bubble',
					label: $i18n.t('settings.personal.interface.chatBubbleUi.label')
				},
				{
					id: 'settings.interface.widescreen_mode',
					label: $i18n.t('settings.personal.interface.widescreenMode.label')
				},
				{
					id: 'settings.interface.floating_action_buttons',
					label: $i18n.t('settings.personal.interface.floatingQuickActions.label')
				},
				{
					id: 'settings.interface.rich_text_input',
					label: $i18n.t('settings.personal.interface.richTextInputForChat.label')
				},
				{
					id: 'settings.interface.large_text_as_file',
					label: $i18n.t('settings.personal.interface.pasteLargeTextAsFile.label')
				},
				{
					id: 'settings.interface.detect_artifacts',
					label: $i18n.t('settings.personal.interface.detectArtifactsAutomatically.label')
				},
				{
					id: 'settings.interface.iframe_sandbox_allow_scripts',
					label: $i18n.t('settings.personal.interface.iframeSandboxAllowScripts.label')
				},
				{
					id: 'settings.interface.iframe_sandbox_allow_same_origin',
					label: $i18n.t('settings.personal.interface.iframeSandboxAllowSameOrigin.label')
				},
				{
					id: 'settings.interface.iframe_sandbox_allow_forms',
					label: $i18n.t('settings.personal.interface.iframeSandboxAllowForms.label')
				},
				{
					id: 'settings.interface.iframe_sandbox_allow_downloads',
					label: $i18n.t('settings.personal.interface.iframeSandboxAllowDownloads.label')
				}
			]
		}
	];

	const setHidden = (id: string, hidden: boolean) => {
		hiddenInterfaceElements = hidden
			? [...hiddenInterfaceElements, id]
			: hiddenInterfaceElements.filter((elementId) => elementId !== id);
	};
</script>

<div class="space-y-0.5">
	{#each groups as group}
		<ModelSettingsSection
			label={group.label}
			summary={group.elements
				.filter((element) => hiddenInterfaceElements.includes(element.id))
				.map((element) => element.label)
				.join(', ') || $i18n.t('None')}
		>
			<div class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
				{#each group.elements as element}
					<ModelSettingToggle
						label={element.label}
						checked={hiddenInterfaceElements.includes(element.id)}
						on:change={(e) => setHidden(element.id, e.detail)}
					/>
				{/each}
			</div>
		</ModelSettingsSection>
	{/each}
</div>
