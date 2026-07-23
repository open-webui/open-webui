<script>
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { updateToolAccessGrants } from '$lib/apis/tools';

	import { extractFrontmatter, formatSkillName, nameToId } from '$lib/utils';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';

	let formElement = null;
	let loading = false;

	let showConfirm = false;
	let showAccessControlModal = false;

	export let edit = false;
	export let clone = false;

	export let onSave = /** @param {any} _value */ async (_value) => {};

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	export let accessGrants = [];

	let _content = '';

	$: if (content) {
		updateContent();
	}

	const updateContent = () => {
		_content = content;
	};

	$: if (name && !edit && !clone) {
		id = nameToId(name);
	}

	let codeEditor;
	let boilerplate = `import os
import requests
from datetime import datetime
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints and descriptions
	
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include a descrption for __user__ as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(
        self,
        equation: str = Field(
            ..., description="The mathematical equation to calculate."
        ),
    ) -> str:
        """
        Calculate the result of an equation.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(
        self,
        city: str = Field(
            "New York, NY", description="Get the current weather for a given city."
        ),
    ) -> str:
        """
        Get the current weather for a given city.
        """

        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
`;

	const saveHandler = async () => {
		loading = true;
		try {
			await onSave({
				id,
				name,
				meta,
				content,
				access_grants: accessGrants
			});
		} finally {
			loading = false;
		}
	};

	const submitHandler = async () => {
		if (codeEditor) {
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

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.tools || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_tools || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && id) {
			try {
				await updateToolAccessGrants(localStorage.token, id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<div class="flex h-full w-full min-w-0 flex-col overflow-hidden">
	<form
		bind:this={formElement}
		class="flex h-full min-h-0 min-w-0 flex-col"
		on:submit|preventDefault={() => {
			if (edit) {
				submitHandler();
			} else {
				showConfirm = true;
			}
		}}
	>
		<button
			class="mb-1 flex h-6 w-fit items-center gap-1 rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
			type="button"
			on:click={() => {
				goto('/workspace/tools');
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<div class="flex shrink-0 items-start gap-2 pb-2 px-1">
			<div class="min-w-0 flex-1">
				<Tooltip content={$i18n.t('e.g. My Tools')} placement="top-start">
					<input
						class="w-full bg-transparent text-sm outline-hidden"
						type="text"
						placeholder={$i18n.t('Tool Name')}
						aria-label={$i18n.t('Tool Name')}
						bind:value={name}
						required
					/>
				</Tooltip>

				<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
					{#if edit}
						<div class="shrink-0 truncate font-mono" title={id}>
							{id}
						</div>
					{:else}
						<Tooltip
							className="min-w-[8rem] flex-1"
							content={$i18n.t('e.g. my_tools')}
							placement="top-start"
						>
							<input
								class="w-full bg-transparent font-mono outline-hidden disabled:text-gray-500"
								type="text"
								placeholder={$i18n.t('Tool ID')}
								aria-label={$i18n.t('Tool ID')}
								bind:value={id}
								required
								disabled={edit}
							/>
						</Tooltip>
					{/if}

					<Tooltip
						className="flex min-w-0 flex-1 items-center"
						content={$i18n.t('e.g. Tools for performing various operations')}
						placement="top-start"
					>
						<input
							class="w-full bg-transparent outline-hidden"
							type="text"
							placeholder={$i18n.t('Tool Description')}
							aria-label={$i18n.t('Tool Description')}
							bind:value={meta.description}
							required
						/>
					</Tooltip>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-1 pr-0.5">
				<AccessButton
					on:click={() => {
						showAccessControlModal = true;
					}}
				/>
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-hidden rounded-lg">
			<CodeEditor
				bind:this={codeEditor}
				value={content}
				lang="python"
				{boilerplate}
				className="text-[11px]"
				onChange={(e) => {
					_content = e;
					if (!edit) {
						const fm = extractFrontmatter(e);
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

		<div class="shrink-0 py-2 text-xs text-gray-500">
			<div class="flex items-center justify-between gap-3">
				<div class="min-w-0">
					<span class="font-normal dark:text-gray-200">{$i18n.t('Warning:')}</span>
					{$i18n.t('Tools can execute arbitrary code.')}
					<span class="font-normal dark:text-gray-400">
						{$i18n.t('Only install tools from sources you trust.')}
					</span>
				</div>

				<button
					class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					type="submit"
					disabled={loading}
				>
					{$i18n.t(edit ? 'Save' : 'Save & Create')}
					{#if loading}
						<Spinner className="size-3" />
					{/if}
				</button>
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
				<li>
					{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}
				</li>
				<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
