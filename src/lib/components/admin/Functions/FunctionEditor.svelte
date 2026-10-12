<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import VersionDiff from '$lib/components/workspace/common/VersionDiff.svelte';
	import FunctionHistory from './FunctionHistory.svelte';
	import { getFunctionHistoryDiff } from '$lib/apis/functions';

	const i18n = getContext<any>('i18n');

	import { extractFrontmatter, formatSkillName, nameToId } from '$lib/utils';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import LocalizedField from '$lib/components/common/LocalizedField.svelte';
	import PluginTranslations from '$lib/components/workspace/common/PluginTranslations.svelte';
	import { pruneEmptyLocaleEntries } from '$lib/utils/localizedContent';
	let locale = '';
	$: warning = [
		$i18n.t('Warning:'),
		$i18n.t('Functions can execute arbitrary code.'),
		$i18n.t('Only install functions from sources you trust.')
	].join(' ');

	let formElement: HTMLFormElement | null = null;
	let loading = false;
	let showConfirm = false;

	export let onSave: (value: any) => Promise<any> = async (_value) => false;

	export let edit = false;
	export let clone = false;

	export let id = '';
	export let version_id: string | null = null;
	export let onProduction: (resource: any) => Promise<void> = async (_resource) => {};
	let selected: any = null;
	let selecting = false;
	let promoting = false;
	let historyControl: { requestPromotion: () => void };
	let commitMessage = '';
	let comparison: any = null;
	let comparing = false;
	let comparisonRequest = 0;
	let comparisonSelection: string | null | undefined = null;
	$: if (selected?.id !== comparisonSelection) {
		comparisonSelection = selected?.id;
		comparison = null;
		comparing = false;
		comparisonRequest++;
	}
	const compareToCurrent = async () => {
		if (!selected || !version_id || comparing) return;
		const request = ++comparisonRequest;
		comparing = true;
		try {
			const result = await getFunctionHistoryDiff(localStorage.token, id, selected.id, version_id);
			if (request === comparisonRequest) comparison = result;
		} catch (error: any) {
			if (request === comparisonRequest) toast.error(error?.detail || String(error));
		} finally {
			if (request === comparisonRequest) comparing = false;
		}
	};
	const applyProduction = async (resource: any) => {
		name = resource.name;
		meta = structuredClone(resource.meta);
		content = resource.content;
		_content = content;
		version_id = resource.version_id;
		commitMessage = '';
		comparison = null;
		savedDraft = draftSnapshot(id, name, meta, content);
	};
	const productionHandler = async (resource: any) => {
		await applyProduction(resource);
		try {
			await onProduction(resource);
		} catch (error: any) {
			toast.error(String(error));
		}
	};
	export let name = '';
	/** @type {{description: string, i18n?: Record<string, Record<string, string>>, manifest?: {translations?: Record<string, Record<string, string>>}}} */
	export let meta: {
		description: string;
		i18n?: Record<string, Record<string, string>>;
		[key: string]: any;
	} = {
		description: ''
	};
	export let content = '';
	let _content = '';
	/** @param {string} id @param {string} name @param {Record<string, any>} meta @param {string} content */
	const draftSnapshot = (id: string, name: string, meta: Record<string, any>, content: string) =>
		JSON.stringify({
			id,
			name,
			meta: {
				...meta,
				manifest: undefined,
				has_user_valves: undefined,
				toggle: undefined,
				i18n: pruneEmptyLocaleEntries(meta.i18n)
			},
			content
		});
	let savedDraft = draftSnapshot(id, name, meta, content);
	$: draft = draftSnapshot(id, name, meta, _content);
	$: changed = draft !== savedDraft;

	$: _content = content;

	$: if (name && !edit && !clone) {
		id = nameToId(name);
	}

	let codeEditor: CodeEditor;
	let starterType = 'filter';
	const filterBoilerplate = `"""
title: Example Filter
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Priority level for the filter operations."
        )
        max_turns: int = Field(
            default=8, description="Maximum allowable conversation turns for a user."
        )
        pass

    class UserValves(BaseModel):
        max_turns: int = Field(
            default=4, description="Maximum allowable conversation turns for a user."
        )
        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        # self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves()
        pass

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{__user__}")

        if __user__.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])

            max_turns = min(__user__["valves"].max_turns, self.valves.max_turns)
            if len(messages) > max_turns:
                raise Exception(
                    f"Conversation turn limit exceeded. Max turns: {max_turns}"
                )

        return body

    def request(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify the request body before each model/provider call.
        print(f"request:{__name__}")
        print(f"request:body:{body}")
        print(f"request:user:{__user__}")

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{__user__}")

        return body
`;
	const eventBoilerplate = `"""
title: Example Event
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1
"""

from pydantic import BaseModel


class Event:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def event(
        self,
        event: dict,
        __event_id__: str = None,
        __event_name__: str = None,
        __id__: str = None,
        __app__=None,
        __request__=None,
    ):
        print(f"event:{__name__}")
        print(f"event:id:{__event_id__}")
        print(f"event:name:{__event_name__}")
        print(f"event:payload:{event}")
`;
	let boilerplate = filterBoilerplate;

	/** @param {'filter' | 'event'} type */
	const setStarterType = (type: 'filter' | 'event') => {
		starterType = type;
		boilerplate = type === 'event' ? eventBoilerplate : filterBoilerplate;
		content = boilerplate;
		_content = boilerplate;
	};

	/** @param {string} value */
	const selectStarterType = (value: string) => {
		setStarterType(value === 'event' ? 'event' : 'filter');
	};

	const _boilerplate = `from pydantic import BaseModel
from typing import Optional, Union, Generator, Iterator
from open_webui.utils.misc import get_last_user_message

import os
import requests


# Filter Class: This class is designed to serve as a pre-processor and post-processor
# for request and response modifications. It checks and transforms requests and responses
# to ensure they meet specific criteria before further processing or returning to the user.
class Filter:
    class Valves(BaseModel):
        max_turns: int = 4
        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves(**{"max_turns": 2})
        pass

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{user}")

        if user.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])
            if len(messages) > self.valves.max_turns:
                raise Exception(
                    f"Conversation turn limit exceeded. Max turns: {self.valves.max_turns}"
                )

        return body

    def request(self, body: dict, user: Optional[dict] = None) -> dict:
        # Modify the request body before each model/provider call.
        print(f"request:{__name__}")
        print(f"request:body:{body}")
        print(f"request:user:{user}")

        return body

    def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{user}")

        messages = [
            {
                **message,
                "content": f"{message['content']} - @@Modified from Filter Outlet",
            }
            for message in body.get("messages", [])
        ]

        return {"messages": messages}



# Pipe Class: This class functions as a customizable pipeline.
# It can be adapted to work with any external or internal models,
# making it versatile for various use cases outside of just OpenAI models.
class Pipe:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
        OPENAI_API_KEY: str = "your-key"
        pass

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()
        self.pipes = self.get_openai_models()
        pass

    def get_openai_models(self):
        if self.valves.OPENAI_API_KEY:
            try:
                headers = {}
                headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
                headers["Content-Type"] = "application/json"

                r = requests.get(
                    f"{self.valves.OPENAI_API_BASE_URL}/models", headers=headers
                )

                models = r.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                    if "gpt" in model["id"]
                ]

            except Exception as e:

                print(f"Error: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Could not fetch models from OpenAI, please update the API Key in the valves.",
                    },
                ]
        else:
            return []

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        if "user" in body:
            print(body["user"])
            del body["user"]

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        model_id = body["model"][body["model"].find(".") + 1 :]
        payload = {**body, "model": model_id}
        print(payload)

        try:
            r = requests.post(
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
`;

	const saveHandler = async () => {
		if (!name.trim() || !meta.description?.trim()) {
			locale = '';
			toast.error($i18n.t('Name and description are required'));
			loading = false;
			return;
		}
		loading = true;
		try {
			const submittedDraft = draftSnapshot(id, name, meta, content);
			const saved = await onSave({
				commit_message: commitMessage || null,
				id,
				name,
				meta: { ...meta, i18n: pruneEmptyLocaleEntries(meta.i18n) },
				content
			});
			if (saved) {
				if (saved.version_id && saved.content !== undefined) await applyProduction(saved);
				else {
					savedDraft = submittedDraft;
					commitMessage = '';
				}
			}
		} finally {
			loading = false;
		}
	};

	const submitHandler = async () => {
		if (selected || selecting || promoting || loading || (edit && !changed)) return;
		if (codeEditor) {
			loading = true;
			content = _content;
			await tick();

			const res = await codeEditor.formatPythonCodeHandler();
			await tick();

			content = _content;
			await tick();

			if (!res) {
				console.warn('Code formatting failed or was skipped, saving unformatted code');
			}

			saveHandler();
		}
	};
</script>

<div class="flex h-full w-full min-w-0 flex-col overflow-hidden">
	<form
		bind:this={formElement}
		class="flex h-full min-h-0 min-w-0 flex-col"
		on:submit|preventDefault={() => {
			if (selected) return;
			if (edit) {
				submitHandler();
			} else {
				showConfirm = true;
			}
		}}
	>
		<div class="flex shrink-0 items-center justify-between gap-2">
			<div class="flex min-w-0 items-center gap-3">
				<button
					class="flex h-6 w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
					type="button"
					on:click={() => {
						goto('/admin/functions');
					}}
				>
					<ChevronLeft className="size-3" strokeWidth="2" />
					<span>{$i18n.t('Back')}</span>
				</button>
				{#if edit && version_id}
					<FunctionHistory
						bind:this={historyControl}
						resource={{ id, version_id }}
						bind:selected
						bind:selecting
						bind:promoting
						dirty={changed || !!commitMessage}
						disabled={loading}
						onProduction={productionHandler}
					/>
				{/if}
			</div>
			<div class="flex shrink-0 items-center gap-1 pr-0.5">
				<LanguageModeSelect
					bind:value={locale}
					translatedLocales={Object.keys(
						pruneEmptyLocaleEntries(selected ? selected.snapshot.meta.i18n : meta.i18n)
					)}
				/>
			</div>
		</div>

		<div class="flex shrink-0 flex-col gap-2 pb-2 px-1 sm:flex-row sm:items-start">
			<div class="min-w-0 w-full flex-1">
				<Tooltip content={$i18n.t('e.g. My Filter')} placement="top-start">
					{#if selected}
						<LocalizedField
							disabled
							showControls={false}
							placeholder={$i18n.t('Function Name')}
							value={selected.snapshot.name}
							translations={selected.snapshot.meta.i18n}
							{locale}
							required
						/>
					{:else}
						<LocalizedField
							placeholder={$i18n.t('Function Name')}
							bind:value={name}
							bind:translations={meta.i18n}
							{locale}
							required
						/>
					{/if}
				</Tooltip>

				<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
					{#if edit}
						<div class="shrink-0 truncate font-mono" title={id}>
							{id}
						</div>
					{:else}
						<Tooltip
							className="min-w-[8rem] flex-1"
							content={$i18n.t('e.g. my_filter')}
							placement="top-start"
						>
							<input
								class="w-full bg-transparent font-mono outline-hidden disabled:text-gray-500"
								type="text"
								placeholder={$i18n.t('Function ID')}
								aria-label={$i18n.t('Function ID')}
								bind:value={id}
								required
								disabled={edit}
							/>
						</Tooltip>
					{/if}

					<Tooltip
						className="flex min-w-0 flex-1 items-center"
						content={$i18n.t('e.g. A filter to remove profanity from text')}
						placement="top-start"
					>
						{#if selected}
							<LocalizedField
								disabled
								showControls={false}
								placeholder={$i18n.t('Function Description')}
								value={selected.snapshot.meta.description}
								translations={selected.snapshot.meta.i18n}
								{locale}
								field="description"
								required
							/>
						{:else}
							<LocalizedField
								placeholder={$i18n.t('Function Description')}
								bind:value={meta.description}
								bind:translations={meta.i18n}
								{locale}
								field="description"
								required
							/>
						{/if}
					</Tooltip>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-1">
				{#if !edit}
					<select
						class="h-7 rounded-lg border border-gray-100 bg-transparent px-2 text-xs outline-hidden dark:border-gray-800"
						bind:value={starterType}
						on:change={(event) => selectStarterType(event.currentTarget.value)}
						aria-label={$i18n.t('Function starter')}
					>
						<option value="filter">{$i18n.t('Filter')}</option>
						<option value="event">{$i18n.t('Event')}</option>
					</select>
				{/if}
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-hidden rounded-lg flex flex-col">
			{#if locale && !comparison}
				{#key selected?.id}
					{#if selected}
						<PluginTranslations
							{id}
							kind="function"
							{locale}
							readOnly
							translations={selected.snapshot.meta.i18n}
						/>
					{:else}
						<PluginTranslations
							id={edit ? id : ''}
							kind="function"
							{locale}
							bind:translations={meta.i18n}
						/>
					{/if}
				{/key}
			{/if}

			{#if comparison}
				<VersionDiff
					currentLabel={$i18n.t('Production')}
					showFileHeaders={false}
					diff={{
						fromId: comparison.from_id,
						toId: comparison.to_id,
						metadata: comparison.metadata,
						files:
							comparison.content_diff || comparison.line_endings_only
								? [{ path: `${id}.py`, status: 'modified', binary: false }]
								: []
					}}
					loadFileDiff={async () => ({
						diff: comparison.content_diff,
						line_endings_only: comparison.line_endings_only
					})}
					onClose={() => {
						comparison = null;
					}}
				/>
			{/if}
			{#if selected && !locale && !comparison}
				<CodeEditor
					value={selected.snapshot.content}
					lang="python"
					readOnly
					className="text-[0.6875rem]"
				/>
			{/if}
			<div class={locale || comparison || selected ? 'hidden' : 'h-full min-h-0'}>
				<CodeEditor
					bind:this={codeEditor}
					value={content}
					readOnly={!!selected || selecting || promoting}
					lang="python"
					{boilerplate}
					className="text-[0.6875rem]"
					onChange={(e: string) => {
						if (selected) return;
						content = e;
						_content = e;
						if (!edit) {
							const fm = extractFrontmatter(e) as Record<string, string>;
							if (fm.title && !name) {
								name = formatSkillName(fm.title);
								id = nameToId(fm.title);
							}
							if (fm.description && !meta.description) {
								meta = { ...meta, description: fm.description };
							}
						}
					}}
					onSave={async () => {
						if (formElement) {
							formElement.requestSubmit();
						}
					}}
				/>
			</div>
		</div>

		<div class="shrink-0 py-2 text-xs text-gray-500">
			<div class="flex items-center justify-between gap-3">
				<Tooltip
					className="min-w-0 flex-1"
					content={warning}
					allowHTML={false}
					placement="top-start"
				>
					<div class="truncate">{warning}</div>
				</Tooltip>

				<div class="ml-auto flex min-w-0 max-w-full shrink-0 items-center gap-3">
					{#if selected}
						{#if !comparison}
							<button
								type="button"
								class="flex h-7 shrink-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
								disabled={comparing || promoting || selecting}
								on:click={compareToCurrent}
							>
								{$i18n.t('Compare to current')}{#if comparing}<Spinner className="size-3" />{/if}
							</button>
						{/if}
						<button
							type="button"
							class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900"
							disabled={promoting || selecting}
							on:click={() => historyControl?.requestPromotion()}
						>
							{$i18n.t('Set as Production')}{#if promoting}<Spinner className="size-3" />{/if}
						</button>
					{:else}
						<input
							class="w-32 min-w-0 flex-1 border-0 bg-transparent text-xs outline-hidden placeholder:text-gray-400"
							aria-label={$i18n.t('Describe this change')}
							placeholder={$i18n.t('Describe this change')}
							bind:value={commitMessage}
							disabled={loading}
						/>
						<button
							class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
							type="submit"
							disabled={loading || selecting || promoting || (edit && !changed)}
						>
							{edit ? $i18n.t('Save') : $i18n.t('Save & Create')}
							{#if loading}
								<Spinner className="size-3" />
							{/if}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</form>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>{$i18n.t('Functions allow arbitrary code execution.')}</li>
				<li>{$i18n.t('Do not install functions from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
