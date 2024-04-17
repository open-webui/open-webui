<script>
	import {
		addTagById,
		deleteTagById,
		getAllChatTags,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { tags as _tags } from '$lib/stores';
	import { onMount } from 'svelte';

	import Tags from '../common/Tags.svelte';

	export let chatId = '';
	let tags = [];

	const getTags = async () => {
		return await getTagsById(localStorage.token, chatId).catch(async (error) => {
			return [];
		});
	};

	const addTag = async (tagName) => {
		const res = await addTagById(localStorage.token, chatId, tagName);
		tags = await getTags();

		await updateChatById(localStorage.token, chatId, {
			tags: tags
		});

		_tags.set(await getAllChatTags(localStorage.token));
	};

	const deleteTag = async (tagName) => {
		const res = await deleteTagById(localStorage.token, chatId, tagName);
		tags = await getTags();

		await updateChatById(localStorage.token, chatId, {
			tags: tags
		});

		_tags.set(await getAllChatTags(localStorage.token));
	};

	onMount(async () => {
		if (chatId) {
			tags = await getTags();
		}
	});
</script>

<Tags {tags} {deleteTag} {addTag} />
