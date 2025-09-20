<script lang="ts">
/**
 * +layout.svelte（路由：(app)/home）—— 页面级布局组件
 *
 * 【主要职责】
 * 1) 提供 Home 区域的整体框架：顶部导航栏（含侧边栏开关 + Tab）与可滚动内容区（<slot/>）。
 * 2) 设置页面 <head><title>：由国际化的“Home”与全局应用名 WEBUI_NAME 拼接而成。
 * 3) 响应全局侧边栏状态 showSidebar：在桌面端（md 断点）为侧边栏预留宽度。
 * 4) 引入 i18n、路由信息 page、功能注册表 functions（供子组件或交互按需使用）。
 * 5) 预留 onMount 钩子（当前空实现），可放置首屏初始化逻辑。
 *
 * 【关键概念】
 * - Svelte Store：在模板中通过 $ 前缀（如 $WEBUI_NAME、$showSidebar）自动订阅并解包为当前值；
 * - SvelteKit Page Store：$page.url.pathname 用于判断当前路径，从而高亮对应的导航 Tab；
 * - TailwindCSS：通过类（如 flex、h-screen、md:hidden、dark:xxx、hover:xxx）描述布局与状态样式。
 */
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, functions } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');
	// 国际化上下文：i18n.t('Home') 会根据当前语言返回“Home/首页/...”

	onMount(async () => {});
	// 生命周期钩子：组件挂载后触发；此处留空，后续可加入首屏初始化逻辑（如数据预取、事件订阅等）
</script>

<!--
  页面头部：设置动态标题
  - {$i18n.t('Home')}：从 i18n 取“Home”的多语言文本
  - {$WEBUI_NAME}：全局应用名（来自 store，默认读取 APP_NAME）
  效果示例：“Home | Open WebUI” 或 “首页 | CerebraUI”
-->
<svelte:head>
	<title>
		{$i18n.t('Home')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<!--
  布局容器：占满视口并根据侧边栏状态自适应宽度
  - flex flex-col：纵向布局，顶部导航 + 内容区
  - w-full h-screen：宽度 100% 且高度等于视口高度
  - max-h-[100dvh]：兼容移动端地址栏收缩的视口高度
  - transition-width duration-200 ease-in-out：宽度变化时过渡动画
  - {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''}：在桌面端（md 断点）为侧边栏预留 260px
-->
<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out max-w-[calc(100%-260px)]"
>
	<!--
    顶部导航栏：
    - backdrop-blur-xl：毛玻璃背景
    - drag-region：在 Electron 外壳中允许该区域拖拽窗口（Web 环境不影响）
    - 内含：左侧侧边栏开关按钮 + 右侧两个 Tab（Notes / Calendar）
  -->
	<nav class="px-2.5 pt-1 backdrop-blur-xl w-full drag-region">
		<div class="flex items-center">
			<!-- 移除侧边栏切换按钮，因为logo+New Chat按钮已经固定 -->

			<div class=" flex w-full">
				<!--
    右侧：导航 Tab 列表
    - overflow-x-auto：当屏幕较窄时允许横向滚动
    - text-sm font-medium：统一字重和字号
    - 每个 <a> 通过检查 $page.url.pathname 是否包含特定子路径来决定是否高亮
  -->
				<div
					class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
				>
					<!--
    Tab：Notes
    - 条件高亮：当 pathname 包含 '/home/notes' 时为当前态（类名留空，走默认激活样式）
    - 否则：使用灰度文本，并在 hover 与 dark 模式下调整可读性
  -->
					<a
						class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/home/notes')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
						href="/playground/notes">{$i18n.t('Notes')}</a
					>

					<!--
    Tab：Calendar
    - 条件高亮：当 pathname 包含 '/playground/calendar' 时为当前态（类名留空）
    - 否则：灰度文本 + hover/dark 反馈
    - href 指向 /playground/completions（与路径判断存在历史命名差异，保持代码一致性）
  -->
					<a
						class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/playground/calendar')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
						href="/playground/completions">{$i18n.t('Calendar')}</a
					>
				</div>
			</div>
		</div>
	</nav>

	<!--
    主内容区：
    - flex-1：占据剩余垂直空间
    - max-h-full + overflow-y-auto：在可用高度内滚动子内容
  -->
	<div class=" flex-1 max-h-full overflow-y-auto">
		<!--
    <slot/>：子路由插槽
    - 渲染位于 (app)/home/ 下的具体页面内容
    - 该布局提供统一的导航与容器，具体内容由子页面决定
  -->
		<slot />
	</div>
</div>
