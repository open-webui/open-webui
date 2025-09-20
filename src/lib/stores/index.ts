import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { Socket } from 'socket.io-client';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

/**
 * -------------------------------
 * 全局状态（Svelte Stores）说明
 * -------------------------------
 * 本文件集中定义了前端可响应的全局状态（Svelte 的 writable/Readable stores），
 * 供应用各处订阅与修改，确保“单一数据源 + 响应式 UI”。
 *
 * 【如何修改应用名称？】
 * - WEBUI_NAME 的初始值来自常量 APP_NAME（见：src/lib/constants.ts）。
 * - 你可以：
 *   1) 在 constants.ts 里修改 APP_NAME 的导出值（构建期/启动时生效）；
 *   2) 或在运行时调用 WEBUI_NAME.set('CerebraUI') 动态覆盖。
 *
 * 【为什么使用 Svelte Store（优势）】
 * 1) 响应式：任意组件用 `$WEBUI_NAME` 订阅后，状态变化会自动触发 UI 更新；
 * 2) 去耦合：状态与视图分离，避免多处手写事件/回调导致的数据不同步；
 * 3) 单一数据源：全局只维护一份状态，便于调试与追踪；
 * 4) 轻量易测：API 简单（set / update / subscribe），逻辑易于单元测试；
 * 5) SSR/CSR 兼容：可与 SvelteKit 的服务端/客户端渲染一起工作（需注意只在浏览器环境访问 window、localStorage 等）。
 *
 * 【使用方法（示例）】
 * - 读取（Svelte 组件模版内）：`{$WEBUI_NAME}`
 * - 读取（脚本中订阅）：
 *    const unsubscribe = WEBUI_NAME.subscribe(v =&gt; console.log(v));
 *    // ... 在 onDestroy 时：unsubscribe();
 * - 修改：
 *    WEBUI_NAME.set('CerebraUI');                 // 覆盖
 *    WEBUI_NAME.update(v =&gt; v + ' Pro');          // 基于旧值更新
 *
 * 【持久化说明】
 * - 本文件中的 store 默认仅驻留内存，不做持久化。
 * - 如需跨刷新保存，建议在 subscribe 中同步到 localStorage，或走后端 API。
 */

/**
 * 应用显示名称（全局）
 * - 初始值：取自 APP_NAME（见 $lib/constants）
 * - 主要用途：浏览器 &lt;title&gt;、导航标题、品牌展示等
 * - 修改方式：
 *    1) 构建期：修改 constants.ts 里的 APP_NAME；
 *    2) 运行时：WEBUI_NAME.set('CerebraUI')
 */
export const WEBUI_NAME = writable(APP_NAME);

/**
 * 后端 / 系统配置（只读快照）
 * - 类型：Config | undefined
 * - 来源：通常由后端 / 配置接口返回后写入
 * - 用途：控制全局功能开关、默认模型、OAuth 提供商等
 * - 注意：为避免“空状态闪烁”，首次为 undefined；渲染时需判空
 */
export const config: Writable<Config | undefined> = writable(undefined);

/**
 * 当前登录用户信息
 * - 类型：SessionUser | undefined
 * - 含义：id / email / name / role / 头像 等
 * - 典型用法：权限控制（显示/隐藏管理员入口）、头像展示、欢迎语
 */
export const user: Writable<SessionUser | undefined> = writable(undefined);

/**
 * Electron 桌面应用相关状态
 * - isApp：当前是否运行在 Electron 外壳中
 * - appInfo / appData：由桌面端注入的应用信息、持久数据（可能为 null）
 */
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

/**
 * 模型下载池（前端可视化进度/状态）
 * - 结构：{ [modelId: string]: { progress?: number; status?: 'pending'|'done'|'error'; ... } }
 * - 用途：统一跟踪/展示模型下载任务的进度条与状态
 */
export const MODEL_DOWNLOAD_POOL = writable({});

/**
 * 终端特征：是否为移动端视口（由响应式检测逻辑写入）
 * - 典型用途：切换布局、隐藏复杂控件、优化手势区域
 */
export const mobile = writable(false);

/**
 * 实时通信与活跃用户
 * - socket：Socket.IO 客户端实例（null 表示未连接）
 * - activeUserIds：当前会话/房间内的活跃用户 ID 列表
 * - USAGE_POOL：用于配额/用量统计的临时缓存（实现因项目而异）
 */
export const socket: Writable<null | Socket> = writable(null);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const USAGE_POOL: Writable<null | string[]> = writable(null);

/**
 * 主题偏好
 * - 可选值：'system' | 'light' | 'dark' | 其他自定义主题键（如 'oled-dark' / 'her'）
 * - 与 app.html 中的启动脚本配合，控制 &lt;html&gt; 上的主题类名与 meta theme-color
 */
export const theme = writable('system');

/**
 * 表情短码映射（:smile: -&gt; 😄）
 * - 数据来自 emoji-shortcodes.json
 * - 构造一个短码到 Emoji 字符的反向索引，供富文本/聊天输入时替换
 */
export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {})
);

/**
 * 语音合成/处理的 Web Worker 句柄
 * - null 表示未初始化
 * - 用于避免在主线程执行重计算，保障 UI 流畅
 */
export const TTSWorker = writable(null);

/**
 * 当前聊天会话标识与标题
 * - chatId：后端/索引的主键 ID
 * - chatTitle：UI 展示用标题，可能由模型自动生成
 */
export const chatId = writable('');
export const chatTitle = writable('');

/**
 * 会话集合与组织
 * - channels：频道列表（如多聊天室/团队空间）
 * - chats：聊天列表或分页数据（null 表示未加载）
 * - pinnedChats：置顶的会话集合
 * - tags：会话/文档的标签集合
 */
export const channels = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);

/**
 * 模型列表（OpenAI / Ollama 等）
 * - 类型：Model[]
 * - 用途：模型选择器、过滤器、元信息展示（参数规模、族群、量化等级等）
 */
export const models: Writable<Model[]> = writable([]);

/**
 * 业务资源
 * - prompts：提示词模板/片段（可为空表示未拉取）
 * - knowledge：知识库文档清单（集合名/文件名/标题）
 * - tools / functions：可调用工具与函数（通常由后端/插件系统注入）
 */
export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable(null);
export const workflows = writable(null);
export const functions = writable(null);

/**
 * 外部工具服务器列表
 * - 例如：工作流编排（LangFlow / n8n）、私有工具网关等
 * - 用于在“工具”配置中进行绑定和路由
 */
export const toolServers = writable([]);

/**
 * 横幅通知
 * - 用于在 UI 顶部展示系统级公告、版本更新提示等
 */
export const banners: Writable<Banner[]> = writable([]);

/**
 * 用户/全局设置
 * - 内容包含：默认模型、对话模式、可读性/可访问性偏好、生成参数（temperature、top_p 等）
 * - 注意：此处仅为前端状态，是否持久化取决于后端或本地存储策略
 */
export const settings: Writable<Settings> = writable({});

/**
 * UI 显隐控制（布尔开关）
 * - 包括：侧边栏、设置抽屉、归档对话、更新日志等弹层
 */
export const showSidebar = writable(false);
export const showSettings = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

/**
 * 其它界面层/浮层控制
 * - showControls：工具条/控制面板
 * - showOverview：概览视图（如模型/会话总览）
 * - showArtifacts：产物面板（代码块/图片/附件等）
 * - showCallOverlay：通话/语音叠加层
 */
export const showControls = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);

/**
 * 会话与分页
 * - temporaryChatEnabled：是否开启临时会话（不入库或匿名态）
 * - scrollPaginationEnabled：是否启用滚动分页（触底自动加载）
 * - currentChatPage：当前分页索引
 */
export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

/**
 * 其他状态
 * - isLastActiveTab：是否为最近使用的标签页（用于通知路由判断）
 * - playingNotificationSound：是否正在播放通知音（避免并发播放）
 */
export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

export type Model = OpenAIModel | OllamaModel;

type BaseModel = {
	id: string;
	name: string;
	info?: ModelConfig;
	owned_by: 'ollama' | 'openai' | 'arena';
};

export interface OpenAIModel extends BaseModel {
	owned_by: 'openai';
	external: boolean;
	source?: string;
}

export interface OllamaModel extends BaseModel {
	owned_by: 'ollama';
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
	ollama?: {
		name?: string;
		model?: string;
		modified_at: string;
		size?: number;
		digest?: string;
		details?: {
			parent_model?: string;
			format?: string;
			family?: string;
			families?: string[];
			parameter_size?: string;
			quantization_level?: string;
		};
		urls?: number[];
	};
}

type OllamaModelDetails = {
	parent_model: string;
	format: string;
	family: string;
	families: string[] | null;
	parameter_size: string;
	quantization_level: string;
};

type Settings = {
	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	title?: TitleSettings;
	splitLargeDeltas?: boolean;
	chatDirection: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;

	system?: string;
	requestFormat?: string;
	keepAlive?: string;
	seed?: number;
	temperature?: string;
	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	num_batch?: string;
	num_keep?: string;
	options?: ModelOptions;
};

type ModelOptions = {
	stop?: boolean;
};

type AudioSettings = {
	STTEngine?: string;
	TTSEngine?: string;
	speaker?: string;
	model?: string;
	nonLocalVoices?: boolean;
};

type TitleSettings = {
	auto?: boolean;
	model?: string;
	modelExternal?: string;
	prompt?: string;
};

type Prompt = {
	command: string;
	user_id: string;
	title: string;
	content: string;
	timestamp: number;
};

type Document = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

type Config = {
	status: boolean;
	name: string;
	version: string;
	default_locale: string;
	default_models: string;
	default_prompt_suggestions: PromptSuggestion[];
	features: {
		auth: boolean;
		auth_trusted_header: boolean;
		enable_api_key: boolean;
		enable_signup: boolean;
		enable_login_form: boolean;
		enable_web_search?: boolean;
		enable_google_drive_integration: boolean;
		enable_onedrive_integration: boolean;
		enable_image_generation: boolean;
		enable_admin_export: boolean;
		enable_admin_chat_access: boolean;
		enable_community_sharing: boolean;
		enable_autocomplete_generation: boolean;
	};
	oauth: {
		providers: {
			[key: string]: string;
		};
	};
};

type PromptSuggestion = {
	content: string;
	title: [string, string];
};

type SessionUser = {
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};
