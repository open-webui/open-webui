<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { WEBUI_NAME, config, functions, models, settings } from '$lib/stores';
	import { onMount, getContext, tick } from 'svelte';

	import { goto } from '$app/navigation';
	import {
		createNewFunction,
		deleteFunctionById,
		exportFunctions,
		getFunctionById,
		getFunctions,
		toggleFunctionById,
		toggleGlobalById
	} from '$lib/apis/functions';

	import ArrowDownTray from '../icons/ArrowDownTray.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import { getModels } from '$lib/apis';
	import FunctionMenu from './Functions/FunctionMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Switch from '../common/Switch.svelte';
	import ValvesModal from '../workspace/common/ValvesModal.svelte';
	import ManifestModal from '../workspace/common/ManifestModal.svelte';
	import Heart from '../icons/Heart.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	let shiftKey = false;

	let functionsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedFunction = null;

	let showDeleteConfirm = false;

	let filteredItems = [];
	$: filteredItems = $functions
		.filter(
			(f) =>
				query === '' ||
				f.name.toLowerCase().includes(query.toLowerCase()) ||
				f.id.toLowerCase().includes(query.toLowerCase())
		)
		.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));

	const shareHandler = async (func) => {
		const item = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/functions/create`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(item), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (func) => {
		const _function = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_function) {
			sessionStorage.function = JSON.stringify({
				..._function,
				id: `${_function.id}_clone`,
				name: `${_function.name} (Clone)`
			});
			goto('/admin/functions/create');
		}
	};

	const exportHandler = async (func) => {
		const _function = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_function) {
			let blob = new Blob([JSON.stringify([_function])], {
				type: 'application/json'
			});
			saveAs(blob, `function-${_function.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (func) => {
		const res = await deleteFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function deleted successfully'));

			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	const toggleGlobalHandler = async (func) => {
		const res = await toggleGlobalById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			if (func.is_global) {
				func.type === 'filter'
					? toast.success($i18n.t('Filter is now globally enabled'))
					: toast.success($i18n.t('Function is now globally enabled'));
			} else {
				func.type === 'filter'
					? toast.success($i18n.t('Filter is now globally disabled'))
					: toast.success($i18n.t('Function is now globally disabled'));
			}

			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	onMount(() => {
		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Functions')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class="flex flex-col gap-3 mt-2 mb-4">
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<div class="flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 dark:from-orange-600 dark:to-orange-700 shadow-lg shadow-orange-500/20">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-6 h-6 text-white"
				>
					<path
						fill-rule="evenodd"
						d="M4.25 2A2.25 2.25 0 002 4.25v11.5A2.25 2.25 0 004.25 18h11.5A2.25 2.25 0 0018 15.75V4.25A2.25 2.25 0 0015.75 2H4.25zm4.03 6.28a.75.75 0 00-1.06-1.06L4.97 9.47a.75.75 0 000 1.06l2.25 2.25a.75.75 0 001.06-1.06L6.56 10l1.72-1.72zm4.5-1.06a.75.75 0 10-1.06 1.06L13.44 10l-1.72 1.72a.75.75 0 101.06 1.06l2.25-2.25a.75.75 0 000-1.06l-2.25-2.25z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div>
				<div class="flex items-center gap-3">
					<h2 class="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
						{$i18n.t('Functions')}
					</h2>
					<span class="px-3 py-1 text-sm font-bold text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 rounded-full">
						{filteredItems.length}
					</span>
				</div>
			</div>
		</div>
	</div>

	<div class="flex w-full gap-3">
		<div class="flex flex-1 items-center gap-3 px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm hover:border-gray-300 dark:hover:border-gray-600 transition-all">
			<Search className="size-4 text-gray-400" />
			<input
				class="w-full text-sm font-medium bg-transparent outline-none text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
				bind:value={query}
				placeholder={$i18n.t('Search Functions')}
			/>
		</div>

		<div>
			<a
				class="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 dark:from-orange-500 dark:to-orange-600 dark:hover:from-orange-600 dark:hover:to-orange-700 text-white transition-all shadow-lg shadow-orange-500/25 hover:shadow-xl hover:shadow-orange-500/30 hover:scale-105 active:scale-95"
				href="/admin/functions/create"
			>
				<Plus className="size-5" />
			</a>
		</div>
	</div>
</div>

<div class="mb-6 space-y-2">
	{#each filteredItems as func (func.id)}
		<div
			class="flex space-x-4 cursor-pointer w-full px-4 py-3.5 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition-all duration-150 border border-transparent hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-md group"
		>
			<a
				class="flex flex-1 space-x-4 cursor-pointer w-full"
				href={`/admin/functions/edit?id=${encodeURIComponent(func.id)}`}
			>
				<div class="flex items-center text-left w-full">
					<div class="flex-1 pl-1">
						<div class="font-semibold flex items-center gap-2 mb-1.5">
							<div
								class="text-xs font-bold px-2 py-0.5 rounded-lg uppercase line-clamp-1 bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 text-gray-700 dark:text-gray-200 shadow-sm"
							>
								{func.type}
							</div>

							{#if func?.meta?.manifest?.version}
								<div
									class="text-xs font-bold px-2 py-0.5 rounded-lg line-clamp-1 bg-gradient-to-r from-blue-100 to-blue-200 dark:from-blue-900/50 dark:to-blue-800/50 text-blue-700 dark:text-blue-200 shadow-sm"
								>
									v{func?.meta?.manifest?.version ?? ''}
								</div>
							{/if}

							<div class="line-clamp-1 text-gray-900 dark:text-white">
								{func.name}
							</div>
						</div>

						<div class="flex gap-2 px-1">
							<div class="text-gray-600 dark:text-gray-400 text-xs font-semibold shrink-0">
								{func.id}
							</div>

							<div class="text-xs text-gray-600 dark:text-gray-400 overflow-hidden text-ellipsis line-clamp-1">
								{func.meta.description}
							</div>
						</div>
					</div>
				</div>
			</a>
			<div class="flex flex-row gap-1 self-center">
				{#if shiftKey}
					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="self-center w-fit text-sm px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all hover:scale-110 active:scale-95"
							type="button"
							on:click={() => {
								deleteHandler(func);
							}}
						>
							<GarbageBin />
						</button>
					</Tooltip>
				{:else}
					{#if func?.meta?.manifest?.funding_url ?? false}
						<Tooltip content={$i18n.t('Support')}>
							<button
								class="self-center w-fit text-sm px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-pink-600 dark:hover:text-pink-400 hover:bg-pink-50 dark:hover:bg-pink-900/20 rounded-xl transition-all hover:scale-110 active:scale-95"
								type="button"
								on:click={() => {
									selectedFunction = func;
									showManifestModal = true;
								}}
							>
								<Heart />
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('Valves')}>
						<button
							class="self-center w-fit text-sm px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-all hover:scale-110 active:scale-95"
							type="button"
							on:click={() => {
								selectedFunction = func;
								showValvesModal = true;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
								/>
							</svg>
						</button>
					</Tooltip>

					<FunctionMenu
						{func}
						editHandler={() => {
							goto(`/admin/functions/edit?id=${encodeURIComponent(func.id)}`);
						}}
						shareHandler={() => {
							shareHandler(func);
						}}
						cloneHandler={() => {
							cloneHandler(func);
						}}
						exportHandler={() => {
							exportHandler(func);
						}}
						deleteHandler={async () => {
							selectedFunction = func;
							showDeleteConfirm = true;
						}}
						toggleGlobalHandler={() => {
							if (['filter', 'action'].includes(func.type)) {
								toggleGlobalHandler(func);
							}
						}}
						onClose={() => {}}
					>
						<button
							class="self-center w-fit text-sm p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-all hover:scale-110 active:scale-95"
							type="button"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</FunctionMenu>
				{/if}

				<div class="self-center ml-1">
					<Tooltip content={func.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
						<Switch
							bind:state={func.is_active}
							on:change={async (e) => {
								toggleFunctionById(localStorage.token, func.id);
								models.set(
									await getModels(
										localStorage.token,
										$config?.features?.enable_direct_connections &&
											($settings?.directConnections ?? null)
									)
								);
							}}
						/>
					</Tooltip>
				</div>
			</div>
		</div>
	{/each}
</div>

<!-- <div class=" text-gray-500 text-xs mt-1 mb-2">
	ⓘ {$i18n.t(
		'Admins have access to all tools at all times; users need tools assigned per model in the workspace.'
	)}
</div> -->

<div class="flex justify-end w-full mb-4">
	<div class="flex gap-3">
		<input
			id="documents-import-input"
			bind:this={functionsImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
			on:change={() => {
				console.log(importFiles);
				showConfirm = true;
			}}
		/>

		<button
			class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 border-2 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-700 dark:text-gray-200 transition-all shadow-sm hover:shadow-md font-semibold text-sm hover:scale-105 active:scale-95"
			on:click={() => {
				functionsImportInputElement.click();
			}}
		>
			<div class="font-semibold line-clamp-1">{$i18n.t('Import Functions')}</div>

			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>

		{#if $functions.length}
			<button
				class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 border-2 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-700 dark:text-gray-200 transition-all shadow-sm hover:shadow-md font-semibold text-sm hover:scale-105 active:scale-95"
				on:click={async () => {
					const _functions = await exportFunctions(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});

					if (_functions) {
						let blob = new Blob([JSON.stringify(_functions)], {
							type: 'application/json'
						});
						saveAs(blob, `functions-export-${Date.now()}.json`);
					}
				}}
			>
				<div class="font-semibold line-clamp-1">{$i18n.t('Export Functions')}</div>

				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						fill-rule="evenodd"
						d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		{/if}
	</div>
</div>

{#if $config?.features.enable_community_sharing}
	<div class="my-16 px-1">
		<div class="text-xl font-bold mb-3 text-gray-900 dark:text-white line-clamp-1">
			{$i18n.t('Made by Open WebUI Community')}
		</div>

		<a
			class="flex cursor-pointer items-center justify-between hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100 dark:hover:from-gray-850 dark:hover:to-gray-800 w-full px-5 py-4 rounded-2xl transition-all border-2 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 shadow-sm hover:shadow-md group hover:scale-[1.02] active:scale-[0.98]"
			href="https://openwebui.com/#open-webui-community"
			target="_blank"
		>
			<div class="self-center">
				<div class="font-bold text-gray-900 dark:text-white line-clamp-1 mb-1">
					{$i18n.t('Discover a function')}
				</div>
				<div class="text-sm font-medium text-gray-600 dark:text-gray-400 line-clamp-1">
					{$i18n.t('Discover, download, and explore custom functions')}
				</div>
			</div>

			<div class="text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors group-hover:translate-x-1 transform transition-transform">
				<ChevronRight />
			</div>
		</a>
	</div>
{/if}

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete function?')}
	on:confirm={() => {
		deleteHandler(selectedFunction);
	}}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class="font-semibold">{selectedFunction.name}</span>.
	</div>
</DeleteConfirmDialog>

<ManifestModal bind:show={showManifestModal} manifest={selectedFunction?.meta?.manifest ?? {}} />
<ValvesModal
	bind:show={showValvesModal}
	type="function"
	id={selectedFunction?.id ?? null}
	on:save={async () => {
		await tick();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	}}
/>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		const reader = new FileReader();
		reader.onload = async (event) => {
			const _functions = JSON.parse(event.target.result);
			console.log(_functions);

			for (const func of _functions) {
				const res = await createNewFunction(localStorage.token, func).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			toast.success($i18n.t('Functions imported successfully'));
			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		};

		reader.readAsText(importFiles[0]);
	}}
>
	<div class="text-sm text-gray-500">
		<div class="bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-xl px-4 py-3 border border-yellow-500/30">
			<div class="font-semibold mb-2">Please carefully review the following warnings:</div>

			<ul class="mt-1 list-disc pl-4 text-xs space-y-1">
				<li>{$i18n.t('Functions allow arbitrary code execution.')}</li>
				<li>{$i18n.t('Do not install functions from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3 font-medium">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>