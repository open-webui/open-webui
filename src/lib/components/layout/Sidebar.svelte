<script lang="ts">
	// ========================= 概览 =========================
	// 这是 WebUI 左侧栏（Sidebar）的 Svelte 组件：
	// 1) 负责渲染左侧导航（搜索、功能入口、频道、会话、设置、用户菜单）。
	// 2) 负责加载数据（文件夹/会话/频道/置顶会话/标签），并处理滚动分页和搜索。
	// 3) 负责移动端交互（点击遮罩收起、边缘滑动手势）。
	// 4) 管理若干全局状态（通过 $lib/stores 提供的 Svelte store）。
	// -------------------------------------------------------

	import { toast } from 'svelte-sonner'; // 轻量通知提示
	import { v4 as uuidv4 } from 'uuid'; // 生成临时文件夹用的随机 id

	import { goto } from '$app/navigation'; // SvelteKit 的前端路由跳转
	import {
		user, // 当前登录用户信息（含头像、姓名、权限等）
		chats, // 左侧栏展示的对话列表（带时间分组）
		settings, // 全局设置（本组件只在底部按钮里打开设置弹窗用到 showSettings）
		showSettings, // 控制设置弹窗的开关
		chatId, // 当前选中的聊天 id（进入聊天页面时会设置）
		tags, // 标签集合（搜索为空时默认加载）
		showSidebar, // 是否展示侧边栏（桌面端固定，移动端可开关）
		mobile, // 是否为移动端视图（由窗口宽度 < BREAKPOINT 计算）
		showArchivedChats, // 归档会话弹窗开关
		pinnedChats, // 置顶的会话列表
		scrollPaginationEnabled, // 是否启用滚动分页（靠近底部会自动加载下一页）
		currentChatPage, // 当前会话分页页码
		temporaryChatEnabled, // 是否处于“临时会话”模式（开启时侧栏内容不可操作）
		channels, // 频道列表
		socket, // 与服务端的 socket 连接（用于加入频道等）
		config, // 站点配置（是否启用频道等开关）
		isApp // 是否为桌面 App 容器（影响样式/拖拽区域）
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	// 从上层 Context 取多语言实例（i18n.t('Key') 做文案本地化）
	const i18n: any = getContext('i18n');

	// —— 调用后端接口的函数 ——
	import {
		deleteChatById, // 本文件未直接使用：删除会话
		getChatList, // 获取会话列表（分页）
		getAllTags, // 获取标签列表
		getChatListBySearchText, // 根据搜索词获取会话列表
		createNewChat, // 本文件未直接使用：创建新会话
		getPinnedChatList, // 获取置顶会话
		toggleChatPinnedStatusById, // 切换会话置顶状态
		getChatPinnedStatusById, // 本文件未直接使用：查询置顶状态
		getChatById, // 通过 id 拉取单个会话（用于拖拽导入时兜底）
		updateChatFolderIdById, // 将会话移出文件夹 / 移动到文件夹
		importChat // 从外部 JSON 导入会话
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { WEBUI_BASE_URL } from '$lib/constants';

	// ——— 子组件（弹窗/条目/图标等） ———
	import ArchivedChatsModal from './Sidebar/ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte'; // 进入视口时触发 on:visible 用于“无限滚动”
	import AddFilesPlaceholder from '../AddFilesPlaceholder.svelte'; // 未直接使用
	import SearchInput from './Sidebar/SearchInput.svelte';
	import Folder from '../common/Folder.svelte'; // 可折叠分区容器
	import Plus from '../icons/Plus.svelte'; // 未直接使用
	import Tooltip from '../common/Tooltip.svelte'; // 未直接使用
	import Folders from './Sidebar/Folders.svelte'; // 文件夹树
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte'; // 新建对话按钮图标
	import Home from '../icons/Home.svelte'; // 预留的"主页"入口图标（已注释）
	
	// Icon components
	import CerebraLogo from '$lib/components/icons/CerebraLogo.svelte';
	import ModelsIcon from '$lib/components/icons/ModelsIcon.svelte';
	import PromptsIcon from '$lib/components/icons/PromptsIcon.svelte';
	import KnowledgeIcon from '$lib/components/icons/KnowledgeIcon.svelte';
	import ToolsIcon from '$lib/components/icons/ToolsIcon.svelte';
	import PlaygroundIcon from '$lib/components/icons/PlaygroundIcon.svelte';
	import WorkflowIcon from '$lib/components/icons/WorkflowIcon.svelte';
	import NewChatIcon from '$lib/components/icons/NewChatIcon.svelte';
	import SearchIcon from '$lib/components/icons/SearchIcon.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';

	// —— 响应式断点：小于 768px 视作移动端 ——
	const BREAKPOINT = 768;

	// —— 本组件内部的局部状态 ——
	let navElement; // 侧栏根节点 DOM（设置拖拽区域用）
	let search = ''; // 搜索框输入值（防抖请求）

	let shiftKey = false; // 是否按住 Shift（支持多选/批量操作时常用，这里用于 ChatItem 的 UI）
	let selectedChatId: string | null = null; // 当前在列表里“被点选”的会话（用于右键/操作）
	let showDropdown = false; // 用户菜单下拉是否展开
	let showPinnedChat = true; // 置顶会话分组是否展开（记忆到 localStorage）
	let showCreateChannel = false; // 创建频道的弹窗

	// —— 会话分页相关 ——
	let chatListLoading = false; // 是否正在拉取下一页
	let allChatsLoaded = false; // 是否已经没有更多会话

	// —— 文件夹相关数据结构 ——
	// folders 是一个对象（id -> folderData），并且给父文件夹挂 childrenIds 数组
	let folders: Record<string, any> = {};
	let newFolderId: string | null = null; // 用于创建后高亮“新文件夹”

	// 初始化文件夹树：两次遍历，第一次建立所有节点，第二次串起父子关系
	const initFolders = async () => {
		const folderList = await getFolders(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [] as any[];
		});

		folders = {};

		// 第一次：把每个 folder 的基本数据写入 folders 映射
		for (const folder of folderList) {
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			// 如果刚创建完成，打上 new 标记（用于 UI 高亮）
			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		// 第二次：把子文件夹 id 收集到父文件夹的 childrenIds，并按更新时间排序
		for (const folder of folderList) {
			if (folder.parent_id) {
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {};
				}
				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	// 创建根级文件夹：
	// 1) 名称为空则报错；2) 与现有重名则自动加序号；3) 先用临时 id 乐观更新，后端成功再刷新
	const createFolder = async (name = 'Untitled') => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder: any) => folder.parent_id === null);
		if (rootFolders.find((f: any) => f.name.toLowerCase() === name.toLowerCase())) {
			let i = 1;
			while (rootFolders.find((f: any) => f.name.toLowerCase() === `${name} ${i}`.toLowerCase())) {
				i++;
			}
			name = `${name} ${i}`;
		}

		// 乐观 UI：先塞一个“临时文件夹”，让用户感知马上创建了
		const tempId = uuidv4();
		folders = {
			...folders,
			tempId: {
				id: tempId,
				name,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, name).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			newFolderId = res.id; // 让新建的文件夹高亮
			await initFolders();
		}
	};

	// 频道初始化：拉取频道列表并写入 store
	const initChannels = async () => {
		await channels.set(await getChannels(localStorage.token));
	};

	// 会话列表初始化：
	// 1) 重置分页；2) 先拉标签/置顶/文件夹；3) 根据是否有搜索词拉第一页；4) 启用滚动分页
	const initChatList = async () => {
		// 重置 + 预取
		tags.set(await getAllTags(localStorage.token));
		pinnedChats.set(await getPinnedChatList(localStorage.token));
		initFolders();

		currentChatPage.set(1);
		allChatsLoaded = false;

		if (search) {
			await chats.set(await getChatListBySearchText(localStorage.token, search, $currentChatPage));
		} else {
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}

		// 开启分页（底部 Loader 进入视口时会触发 loadMoreChats）
		scrollPaginationEnabled.set(true);
	};

	// 滚动加载下一页
	const loadMoreChats = async () => {
		chatListLoading = true;
		currentChatPage.set($currentChatPage + 1);

		let newChatList: any[] = [];
		if (search) {
			newChatList = await getChatListBySearchText(localStorage.token, search, $currentChatPage);
		} else {
			newChatList = await getChatList(localStorage.token, $currentChatPage);
		}

		// 如果返回 0 条则标记“已全部加载”
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...($chats ? $chats : []), ...newChatList]);
		chatListLoading = false;
	};

	// 搜索输入防抖：1s 不输入就发请求；清空则恢复默认列表
	let searchDebounceTimeout: any;
	const searchDebounceHandler = async () => {
		console.log('search', search);
		chats.set(null); // 置空先显示 Loading

		if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);

		if (search === '') {
			await initChatList();
			return;
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				allChatsLoaded = false;
				currentChatPage.set(1);
				await chats.set(await getChatListBySearchText(localStorage.token, search));

				// 若无结果，刷新一次标签，方便用户做二次筛选
				if ($chats.length === 0) {
					tags.set(await getAllTags(localStorage.token));
				}
			}, 1000);
		}
	};

	// 批量导入会话（支持从 JSON 文件/拖拽导入）
	const importChatHandler = async (items, pinned = false, folderId: string | null = null) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			if (item.chat) {
				await importChat(localStorage.token, item.chat, item?.meta ?? {}, pinned, folderId);
			}
		}
		initChatList(); // 刷新侧栏
	};

	// 处理拖拽进来的文件（JSON）
	const inputFilesHandler = async (files: File[]) => {
		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = (e.target as any).result;
				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error($i18n.t(`Invalid file format.`));
				}
			};
			reader.readAsText(file);
		}
	};

	// 监听标签增删后，刷新会话列表（保持和后台一致）
	const tagEventHandler = async (type, tagName, chatId) => {
		if (type === 'delete' || type === 'add') {
			initChatList();
		}
	};

	// —— 拖拽进入侧栏的视觉反馈 ——
	let draggedOver = false; // 是否有“文件”拖入（只对文件给出高亮）
	const onDragOver = (e: DragEvent) => {
		e.preventDefault();
		draggedOver = !!e.dataTransfer?.types?.includes('Files');
	};
	const onDragLeave = () => {
		draggedOver = false;
	};
	const onDrop = async (e: DragEvent) => {
		e.preventDefault();
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer.files);
			if (inputFiles.length > 0) inputFilesHandler(inputFiles);
		}
		draggedOver = false;
	};

	// —— 移动端边缘滑动：从屏幕左缘左右滑，开/关侧栏 ——
	let touchstart: Touch; let touchend: Touch;
	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
		// 仅当从左侧 40px 内开始滑，并且滑动距离 >= 屏宽 1/8 时生效
		if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) showSidebar.set(false); // 左滑关闭
			if (touchend.screenX > touchstart.screenX) showSidebar.set(true);  // 右滑打开
		}
	}
	const onTouchStart = (e: TouchEvent) => { touchstart = e.changedTouches[0]; };
	const onTouchEnd = (e: TouchEvent) => { touchend = e.changedTouches[0]; checkDirection(); };

	// —— 键盘事件：仅用于记录是否按住 Shift ——
	const onKeyDown = (e: KeyboardEvent) => { if (e.key === 'Shift') shiftKey = true; };
	const onKeyUp = (e: KeyboardEvent) => { if (e.key === 'Shift') shiftKey = false; };
	const onFocus = () => {};
	const onBlur = () => { shiftKey = false; selectedChatId = null; };

	// —— 生命周期：挂载时初始化、注册事件；卸载时清理 ——
	onMount(async () => {
		// 读取“置顶分组是否展开”的记忆
		showPinnedChat = localStorage?.showPinnedChat ? localStorage.showPinnedChat === 'true' : true;

		// 根据 mobile 状态决定侧栏显示，以及给 <nav> 设置可拖拽区域（桌面 App 用）
		mobile.subscribe((value) => {
			if ($showSidebar && value) {
				// 当从桌面切到移动端时，收起侧栏（避免遮挡）
				showSidebar.set(false);
			}
			if ($showSidebar && !value) {
				const navElement = document.getElementsByTagName('nav')[0];
				if (navElement) navElement.style['-webkit-app-region'] = 'drag';
			}
			if (!$showSidebar && !value) {
				showSidebar.set(true);
			}
		});

		// 初始显示取自本地存储（桌面端记忆展开/收起；移动端默认收起）
		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);
		showSidebar.subscribe((value) => {
			localStorage.sidebar = String(value);
			const navElement = document.getElementsByTagName('nav')[0];
			if (navElement) {
				if ($mobile) {
					navElement.style['-webkit-app-region'] = value ? 'no-drag' : 'drag';
				} else {
					navElement.style['-webkit-app-region'] = 'drag';
				}
			}
		});

		// 预加载频道 & 会话
		await initChannels();
		await initChatList();

		// 全局事件监听
		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);
		window.addEventListener('focus', onFocus);
		window.addEventListener('blur-sm', onBlur); // 自定义事件名（框架内触发）

		// 侧栏拖拽导入文件
		const dropZone = document.getElementById('sidebar');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		// 清理所有监听器，避免内存泄漏
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);
		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchend', onTouchEnd);
		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur-sm', onBlur);
		const dropZone = document.getElementById('sidebar');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	on:change={async () => {
		await initChatList();
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async ({ name, access_control }) => {
		const res = await createNewChannel(localStorage.token, {
			name: name,
			access_control: access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
		}
	}}
/>

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class=" {$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<div
	bind:this={navElement}
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
		? 'md:relative w-[260px] max-w-[260px]'
		: '-translate-x-[260px] w-[0px]'} {$isApp
		? `ml-[4.5rem] md:ml-0 `
		: 'transition-width duration-200 ease-in-out'}  shrink-0 bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-200 text-sm fixed z-50 top-0 left-0 overflow-x-hidden
        "
	data-state={$showSidebar}
>
	<div
		class="py-2 my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[260px] overflow-x-hidden z-50 {$showSidebar
			? ''
			: 'invisible'}"
	>
		<div class="px-1.5 flex items-center justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 bg-gray-50/80 dark:bg-gray-950/80 backdrop-blur-xl">
			<button
				class=" flex items-center rounded-xl px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				on:click={() => {
					// 点击 Logo + 文本切换侧边栏展开/折叠
					showSidebar.set(!$showSidebar);
				}}
				aria-label="Toggle Sidebar"
			>
                <!-- Cerebra Logo (PNG with theme switching) -->
                <CerebraLogo className=" size-10 mr-2" />
				<span class=" font-semibold text-xl">CerebraUI</span>
			</button>

			<a
				id="sidebar-new-chat-button"
				class="flex items-center rounded-lg px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-900 transition no-drag-region"
				href="/"
				draggable="false"
				on:click={async () => {
					selectedChatId = null;
					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
						if ($mobile) {
							showSidebar.set(false);
						}
					}, 0);
				}}
				aria-label="New Chat"
			>
				<NewChatIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
			</a>
		</div>

		<!-- {#if $user?.role === 'admin'}
			<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
				<a
					class="grow flex items-center space-x-3 rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/home"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div class="self-center">
						<Home strokeWidth="2" className="size-[1.1rem]" />
					</div>

					<div class="flex self-center translate-y-[0.5px]">
						<div class=" self-center font-medium text-sm font-primary">{$i18n.t('Home')}</div>
					</div>
				</a>
			</div>
		{/if} -->

		<!-- Workspace 快捷入口移除，改为 Features 分区中的具体项 -->

		<div class="relative mt-4{$temporaryChatEnabled ? 'opacity-20' : ''}">
			{#if $temporaryChatEnabled}
				<div class="absolute z-40 w-full h-full flex justify-center"></div>
			{/if}

			<SearchInput
				bind:value={search}
				on:input={searchDebounceHandler}
				placeholder={$i18n.t('Search')}
				showClearButton={true}
			/>
		</div>

		<div
			class="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden {$temporaryChatEnabled
				? 'opacity-20'
				: ''}"
		>
			<!-- Features Section (collapsible like Chats) -->
			<Folder
				collapsible={!search}
				className="px-2 mt-4"
				name={$i18n.t('Features')}
				dragAndDrop={false}
			>
				<div class="flex flex-col gap-1 pb-1">
					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
						<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/workspace/models" draggable="false">
							<ModelsIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
							<span class=" text-sm">{$i18n.t('Models')}</span>
						</a>
					{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts}
						<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/workspace/prompts" draggable="false">
							<PromptsIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
							<span class=" text-sm">{$i18n.t('Prompts')}</span>
						</a>
					{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
						<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/workspace/knowledge" draggable="false">
							<KnowledgeIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
							<span class=" text-sm">{$i18n.t('Knowledge')}</span>
						</a>
					{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
						<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/workspace/tools" draggable="false">
							<ToolsIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
							<span class=" text-sm">{$i18n.t('Tools')}</span>
						</a>
					{/if}

					<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/workspace/workflows" draggable="false">
						<WorkflowIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
						<span class=" text-sm">{$i18n.t('Workflows')}</span>
					</a>

					{#if $user?.role === 'admin'}
						<a class="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition" href="/playground" draggable="false">
							<PlaygroundIcon className=" size-5 text-gray-900 dark:text-white" strokeWidth="1.8" />
							<span class=" text-sm">{$i18n.t('Playground')}</span>
						</a>
					{/if}
				</div>
			</Folder>
			{#if $config?.features?.enable_channels && ($user?.role === 'admin' || $channels.length > 0) && !search}
				<Folder
					className="px-2 mt-0.5"
					name={$i18n.t('Channels')}
					dragAndDrop={false}
					onAdd={async () => {
						if ($user?.role === 'admin') {
							await tick();

							setTimeout(() => {
								showCreateChannel = true;
							}, 0);
						}
					}}
					onAddLabel={$i18n.t('Create Channel')}
				>
					{#each $channels as channel}
						<ChannelItem
							{channel}
							onUpdate={async () => {
								await initChannels();
							}}
						/>
					{/each}
				</Folder>
			{/if}

			<Folder
				collapsible={!search}
				className="px-2 mt-4"
				name={$i18n.t('Chats')}
				onAdd={() => {
					createFolder();
				}}
				onAddLabel={$i18n.t('New Folder')}
				on:import={(e) => {
					importChatHandler(e.detail);
				}}
				on:drop={async (e) => {
					const { type, id, item } = e.detail;

					if (type === 'chat') {
						let chat = await getChatById(localStorage.token, id).catch((error) => {
							return null;
						});
						if (!chat && item) {
							chat = await importChat(localStorage.token, item.chat, item?.meta ?? {});
						}

						if (chat) {
							console.log(chat);
							if (chat.folder_id) {
								const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);
							}

							if (chat.pinned) {
								const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
							}

							initChatList();
						}
					} else if (type === 'folder') {
						if (folders[id].parent_id === null) {
							return;
						}

						const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
							(error) => {
								toast.error(`${error}`);
								return null;
							}
						);

						if (res) {
							await initFolders();
						}
					}
				}}
			>
				{#if $temporaryChatEnabled}
					<div class="absolute z-40 w-full h-full flex justify-center"></div>
				{/if}

				{#if !search && $pinnedChats.length > 0}
					<div class="flex flex-col space-y-1 rounded-xl">
						<Folder
							className=""
							bind:open={showPinnedChat}
							on:change={(e) => {
								localStorage.setItem('showPinnedChat', e.detail);
								console.log(e.detail);
							}}
							on:import={(e) => {
								importChatHandler(e.detail, true);
							}}
							on:drop={async (e) => {
								const { type, id, item } = e.detail;

								if (type === 'chat') {
									let chat = await getChatById(localStorage.token, id).catch((error) => {
										return null;
									});
									if (!chat && item) {
										chat = await importChat(localStorage.token, item.chat, item?.meta ?? {});
									}

									if (chat) {
										console.log(chat);
										if (chat.folder_id) {
											const res = await updateChatFolderIdById(
												localStorage.token,
												chat.id,
												null
											).catch((error) => {
												toast.error(`${error}`);
												return null;
											});
										}

										if (!chat.pinned) {
											const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
										}

										initChatList();
									}
								}
							}}
							name={$i18n.t('Pinned')}
						>
							<div
								class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900"
							>
								{#each $pinnedChats as chat, idx}
									<ChatItem
										className=""
										id={chat.id}
										title={chat.title}
										{shiftKey}
										selected={selectedChatId === chat.id}
										on:select={() => {
											selectedChatId = chat.id;
										}}
										on:unselect={() => {
											selectedChatId = null;
										}}
										on:change={async () => {
											initChatList();
										}}
										on:tag={(e) => {
											const { type, name } = e.detail;
											tagEventHandler(type, name, chat.id);
										}}
									/>
								{/each}
							</div>
						</Folder>
					</div>
				{/if}

				{#if !search && folders}
					<Folders
						{folders}
						on:import={(e) => {
							const { folderId, items } = e.detail;
							importChatHandler(items, false, folderId);
						}}
						on:update={async (e) => {
							initChatList();
						}}
						on:change={async () => {
							initChatList();
						}}
					/>
				{/if}

				<div class=" flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
					<div class="pt-1.5">
						{#if $chats}
							{#each $chats as chat, idx}
								{#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
									<div
										class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium {idx ===
										0
											? ''
											: 'pt-5'} pb-1.5"
									>
										{$i18n.t(chat.time_range)}
										<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
									</div>
								{/if}

								<ChatItem
									className=""
									id={chat.id}
									title={chat.title}
									{shiftKey}
									selected={selectedChatId === chat.id}
									on:select={() => {
										selectedChatId = chat.id;
									}}
									on:unselect={() => {
										selectedChatId = null;
									}}
									on:change={async () => {
										initChatList();
									}}
									on:tag={(e) => {
										const { type, name } = e.detail;
										tagEventHandler(type, name, chat.id);
									}}
								/>
							{/each}

							{#if $scrollPaginationEnabled && !allChatsLoaded}
								<Loader
									on:visible={(e) => {
										if (!chatListLoading) {
											loadMoreChats();
										}
									}}
								>
									<div
										class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">Loading...</div>
									</div>
								</Loader>
							{/if}
						{:else}
							<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">Loading...</div>
							</div>
						{/if}
					</div>
				</div>
			</Folder>
		</div>

		<!-- Separator line above Settings -->
		<hr class="border-gray-200 dark:border-gray-700 mx-2 my-4" />

		<div class="px-2">
			<!-- Bottom Settings button: open Settings modal -->
			<button
				class="flex items-center rounded-xl py-2.5 px-2.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition mb-1"
				on:click={async () => {
					await showSettings.set(true);
					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="size-5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
				</div>
				<div class=" self-center font-medium text-sm">{$i18n.t('Settings')}</div>
			</button>
			<div class="flex flex-col font-primary">
				{#if $user !== undefined && $user !== null}
					<UserMenu
						role={$user?.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							class=" flex items-center rounded-xl py-2.5 px-2.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div class=" self-center mr-3">
								{#if $user?.profile_image_url}
									<img
										src={$user?.profile_image_url}
										class="size-5 object-cover rounded-full bg-white"
										alt="User profile"
										onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
									/>
									<div class="size-5 bg-white rounded-full flex items-center justify-center" style="display: none;">
										<UserIcon className="size-4 text-gray-700" strokeWidth="1.8" />
									</div>
								{:else}
									<div class="size-5 bg-white rounded-full flex items-center justify-center">
										<UserIcon className="size-4 text-gray-700" strokeWidth="1.8" />
									</div>
								{/if}
							</div>
							<div class=" self-center font-medium text-sm">{$user?.name}</div>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	/* 隐藏滚动条拇指，只有 hover/focus/active 时可见，避免视觉噪点 */
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb { visibility: visible; }
	.scrollbar-hidden::-webkit-scrollbar-thumb { visibility: hidden; }
</style>
