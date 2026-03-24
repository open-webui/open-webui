<script>
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import { goto } from '$app/navigation';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';

	let formElement = null;
	let loading = false;

	let showConfirm = false;
	let showAccessControlModal = false;

	export let edit = false;
	export let clone = false;

	export let onSave = () => {};

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	export let accessControl = {};

	let _content = '';

	$: if (content) {
		updateContent();
	}

	const updateContent = () => {
		_content = content;
	};

	$: if (name && !edit && !clone) {
		id = name.replace(/\s+/g, '_').toLowerCase();
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
		onSave({
			id,
			name,
			meta,
			content,
			access_control: accessControl
		});
	};

	const submitHandler = async () => {
		if (codeEditor) {
			content = _content;
			await tick();

			const res = await codeEditor.formatPythonCodeHandler();
			await tick();

			content = _content;
			await tick();

			if (res) {
				console.log('Code formatted successfully');

				saveHandler();
			}
		}
	};
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	allowPublic={$user?.permissions?.sharing?.public_tools || $user?.role === 'admin'}
/>

<div class="flex flex-col justify-between w-full overflow-y-auto h-full bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
	<div class="mx-auto w-full h-full flex flex-col">
		<form
			bind:this={formElement}
			class="flex flex-col max-h-[100dvh] h-full p-2 sm:p-4 gap-3 sm:gap-4"
			on:submit|preventDefault={() => {
				if (edit) {
					submitHandler();
				} else {
					showConfirm = true;
				}
			}}
		>
			<!-- Header Card -->
			<div class="bg-white dark:bg-gray-800 rounded-lg sm:rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
				<!-- Header Section -->
				<div class="bg-gradient-to-r from-orange-50 to-orange-50 dark:from-orange-950/30 dark:to-amber-950/30 px-3 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-gray-700">
					<div class="flex items-center gap-2 sm:gap-3">
						<!-- Back Button -->
						
						<!-- Icon and Title -->
						<div class="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
							<div class="p-1.5 sm:p-2.5 bg-blue-500/10 dark:bg-blue-500/20 rounded-lg shrink-0">
								<svg class="w-4 h-4 sm:w-6 sm:h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
								</svg>
							</div>
							<div class="flex-1 min-w-0">
								<Tooltip content={$i18n.t('e.g. My Tools')} placement="top-start">
									<input
										class="w-full text-base sm:text-xl lg:text-2xl font-bold bg-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 truncate"
										type="text"
										placeholder={$i18n.t('Tool Name')}
										bind:value={name}
										required
									/>
								</Tooltip>
							</div>
						</div>

						<!-- Access Control Button -->
						<div class="shrink-0">
							<button
								class="group relative px-2.5 sm:px-3.5 py-1.5 sm:py-2.5 bg-white hover:bg-gray-50 dark:bg-gray-900 dark:hover:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 transition-all duration-200 rounded-lg sm:rounded-xl flex gap-1 sm:gap-2 items-center hover:border-blue-300 dark:hover:border-blue-700 shadow-sm"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3 sm:size-4 text-gray-600 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
								<div class="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 hidden sm:inline">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>
				</div>

				<!-- Metadata Section -->
				<div class="px-3 sm:px-6 py-3 sm:py-4 bg-white dark:bg-gray-800">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
						<!-- Tool ID -->
						<div class="space-y-1.5 sm:space-y-2">
							<label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
								{$i18n.t('Tool ID')}
							</label>
							{#if edit}
								<div class="text-xs sm:text-sm text-gray-700 dark:text-gray-300 font-mono bg-gray-50 dark:bg-gray-900 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-gray-200 dark:border-gray-700">
									{id}
								</div>
							{:else}
								<Tooltip content={$i18n.t('e.g. my_tools')} placement="top-start">
									<input
										class="w-full text-xs sm:text-sm font-mono bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-lg px-2.5 sm:px-3 py-1.5 sm:py-2 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
										type="text"
										placeholder={$i18n.t('Tool ID')}
										bind:value={id}
										required
										disabled={edit}
									/>
								</Tooltip>
							{/if}
						</div>

						<!-- Tool Description -->
						<div class="space-y-1.5 sm:space-y-2">
							<label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
								{$i18n.t('Tool Description')}
							</label>
							<Tooltip content={$i18n.t('e.g. Tools for performing various operations')} placement="top-start">
								<input
									class="w-full text-xs sm:text-sm bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-lg px-2.5 sm:px-3 py-1.5 sm:py-2 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none"
									type="text"
									placeholder={$i18n.t('Tool Description')}
									bind:value={meta.description}
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>
			</div>

			<!-- Code Editor Card -->
			<div class="flex-1 overflow-hidden bg-white dark:bg-gray-800 rounded-lg sm:rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 flex flex-col min-h-0">
				<!-- Code Editor Header -->
				<div class="px-3 sm:px-6 py-2 sm:py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between gap-2">
					<div class="flex items-center gap-2 min-w-0">
						<svg class="w-3 h-3 sm:w-4 sm:h-4 text-gray-500 dark:text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
						</svg>
						<span class="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300 truncate">Python Code</span>
						<span class="text-xs px-1.5 sm:px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full font-medium shrink-0">
							.py
						</span>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
						Press <kbd class="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-mono">Ctrl+S</kbd> to save
					</div>
				</div>

				<!-- Code Editor Content -->
				<div class="flex-1 overflow-auto min-h-0">
					<CodeEditor
						bind:this={codeEditor}
						value={content}
						lang="python"
						{boilerplate}
						onChange={(e) => {
							_content = e;
						}}
						onSave={async () => {
							if (formElement) {
								formElement.requestSubmit();
							}
						}}
					/>
				</div>
			</div>

			<!-- Footer Card -->
			<div class="bg-white dark:bg-gray-800 rounded-lg sm:rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
				<div class="px-3 sm:px-6 py-3 sm:py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
					<!-- Warning Message -->
					<div class="flex-1 w-full sm:w-auto">
						<div class="flex items-start gap-2 sm:gap-3 p-2 sm:p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-lg">
							<svg class="w-4 h-4 sm:w-5 sm:h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							<div class="text-xs leading-relaxed">
								<p class="font-semibold text-amber-900 dark:text-amber-200 mb-0.5">
									{$i18n.t('Warning:')}
								</p>
								<p class="text-xs sm:text-xs text-amber-800 dark:text-amber-300">
									{$i18n.t('Tools are a function calling system with arbitrary code execution')}
									— <span class="font-medium">{$i18n.t(`don't install random tools from sources you don't trust.`)}</span>
								</p>
							</div>
						</div>
					</div>

					<!-- Action Buttons -->
					<div class="flex items-center justify-end gap-2 sm:gap-3 w-full sm:w-auto">
						<button
							type="button"
							class="px-3 sm:px-5 py-2 sm:py-2.5 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 border border-gray-300 dark:border-gray-600 rounded-lg transition-all duration-200 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700"
							on:click={() => {
								goto('/workspace/tools');
							}}
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							class="group relative px-4 sm:px-6 py-2 sm:py-2.5 text-xs sm:text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-600 hover:from-blue-700 hover:to-blue-700 rounded-lg sm:rounded-xl transition-all duration-200 focus:ring-4 focus:ring-blue-500/30 shadow-lg shadow-blue-500/25 flex items-center gap-1.5 sm:gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-600 disabled:hover:to-blue-600"
							type="submit"
							disabled={loading}
						>
							<span class="font-semibold">{$i18n.t('Save')}</span>
							{#if loading}
								<svg class="w-3 h-3 sm:w-4 sm:h-4 animate-spin" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
									<path opacity=".25" d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" />
									<path d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z" class="spinner_ajPY" />
								</svg>
							{:else}
								<svg class="w-3 h-3 sm:w-4 sm:h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
							{/if}
						</button>
					</div>
				</div>
			</div>
		</form>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-200 rounded-xl px-5 py-4">
			<div class="flex items-start gap-3 mb-3">
				<svg class="w-6 h-6 text-amber-600 dark:text-amber-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
				</svg>
				<div>
					<p class="font-bold text-base mb-2">{$i18n.t('Please carefully review the following warnings:')}</p>
					<ul class="space-y-1.5 text-sm">
						<li class="flex items-start gap-2">
							<span class="text-amber-600 dark:text-amber-400 mt-1">•</span>
							<span>{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-amber-600 dark:text-amber-400 mt-1">•</span>
							<span>{$i18n.t('Do not install tools from sources you do not fully trust.')}</span>
						</li>
					</ul>
				</div>
			</div>
		</div>

		<div class="mt-4 text-gray-700 dark:text-gray-300 leading-relaxed">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>

<style>
	.spinner_ajPY {
		transform-origin: center;
		animation: spinner_AtaB 0.75s infinite linear;
	}
	@keyframes spinner_AtaB {
		100% {
			transform: rotate(360deg);
		}
	}
</style>