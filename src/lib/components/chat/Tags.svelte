<script>
	import {
		addTagById,
		deleteTagById,
		getAllChatTags,
		getChatList,
		getChatListByTagName,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { tags as _tags, chats } from '$lib/stores';
	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher();

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

		console.log($_tags);

		await _tags.set(await getAllChatTags(localStorage.token));

		console.log($_tags);

		if ($_tags.map((t) => t.name).includes(tagName)) {
			await chats.set(await getChatListByTagName(localStorage.token, tagName));

			if ($chats.find((chat) => chat.id === chatId)) {
				dispatch('close');
			}
		} else {
			await chats.set(await getChatList(localStorage.token));
		}
	};

	onMount(async () => {
		if (chatId) {
			tags = await getTags();
		}
	});
</script>

<Tags {tags} {deleteTag} {addTag} />
