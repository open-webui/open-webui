<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	import { getModelById, updateModelAccessGrants } from '$lib/apis/models';
	import { getKnowledgeById, updateKnowledgeAccessGrants } from '$lib/apis/knowledge';
	import { getPromptById, updatePromptAccessGrants } from '$lib/apis/prompts';
	import { getSkillById, updateSkillAccessGrants } from '$lib/apis/skills';
	import { getToolById, updateToolAccessGrants } from '$lib/apis/tools';
	import AccessControlModal from './AccessControlModal.svelte';

	export let resourceType: 'models' | 'knowledge' | 'prompts' | 'skills' | 'tools';
	export let onUpdated: () => void | Promise<void> = () => {};
	const i18n = getContext<any>('i18n');
	const loaders = {
		models: getModelById,
		knowledge: getKnowledgeById,
		prompts: getPromptById,
		skills: getSkillById,
		tools: getToolById
	};
	const savers = {
		knowledge: updateKnowledgeAccessGrants,
		prompts: updatePromptAccessGrants,
		skills: updateSkillAccessGrants,
		tools: updateToolAccessGrants
	};
	let show = false;
	let saving = false;
	let resource: any = null;
	let accessGrants: any[] = [];
	let savedGrants: any[] = [];
	let requestId = 0;
	const reportError = (error: any) => toast.error(`${error?.detail ?? error}`);

	export const open = async (id: string) => {
		const request = ++requestId;
		show = false;
		try {
			const result = await loaders[resourceType](localStorage.token, id);
			if (request !== requestId) return;
			resource = result;
			accessGrants = structuredClone(result.access_grants ?? []);
			savedGrants = structuredClone(accessGrants);
			saving = false;
			show = true;
		} catch (error) {
			if (request === requestId) reportError(error);
		}
	};

	const save = async (grants: any[]) => {
		if (saving || !resource) return;
		const request = requestId;
		saving = true;
		try {
			const updated =
				resourceType === 'models'
					? await updateModelAccessGrants(localStorage.token, resource.id, resource.name, grants)
					: await savers[resourceType](localStorage.token, resource.id, grants);
			if (request === requestId) {
				accessGrants = structuredClone(updated.access_grants ?? []);
				savedGrants = structuredClone(accessGrants);
			}
			toast.success($i18n.t('Saved'));
		} catch (error) {
			if (request === requestId) accessGrants = structuredClone(savedGrants);
			reportError(error);
			return;
		} finally {
			if (request === requestId) saving = false;
		}
		try {
			await onUpdated();
		} catch (error) {
			reportError(error);
		}
	};
</script>

<AccessControlModal
	bind:show
	bind:accessGrants
	disabled={saving}
	accessRoles={resourceType === 'models' && !resource?.base_model_id ? ['read'] : ['read', 'write']}
	share={$user?.permissions?.sharing?.[resourceType] || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.[`public_${resourceType}`] || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) || $user?.role === 'admin'}
	onChange={save}
/>
