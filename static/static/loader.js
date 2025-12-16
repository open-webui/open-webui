// static/loader.js
(function () {
    const LOG_PREFIX = "[custom-loader]";

    /**
     * Utility: wait for a selector to exist in the DOM
     */
    function waitForSelector(selector, root = document, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const found = root.querySelector(selector);
            if (found) return resolve(found);

            const observer = new MutationObserver(() => {
                const el = root.querySelector(selector);
                if (el) {
                    observer.disconnect();
                    resolve(el);
                }
            });

            observer.observe(
                root === document ? document.documentElement : root,
                { childList: true, subtree: true }
            );

            if (timeout) {
                setTimeout(() => {
                    observer.disconnect();
                    reject(new Error("Timeout waiting for " + selector));
                }, timeout);
            }
        });
    }

    /* ------------------------------------------------
     * 1) Sidebar title: keep forcing "OpenAwesome"
     *    even after Svelte re-renders / sidebar toggles
     * ---------------------------------------------- */

    function initSidebarTitleWatcher() {
        function applyName(root) {
            const el = root.querySelector("#sidebar-webui-name");
            if (el && el.textContent !== "OpenAwesome") {
                el.textContent = "OpenAwesome";
            }
        }

        // One-shot for initial load
        waitForSelector("#sidebar-webui-name")
            .then((el) => {
                if (el.textContent !== "OpenAwesome") {
                    el.textContent = "OpenAwesome";
                }
            })
            .catch((err) => console.warn(LOG_PREFIX, err.message));

        // Global observer to handle re-renders / sidebar reopen
        const docObserver = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (!(node instanceof HTMLElement)) continue;
                    if (node.id === "sidebar-webui-name") {
                        if (node.textContent !== "OpenAwesome") {
                            node.textContent = "OpenAwesome";
                        }
                    } else {
                        applyName(node);
                    }
                }
            }
        });

        docObserver.observe(document.documentElement, {
            childList: true,
            subtree: true,
        });
    }

    /* ------------------------------------------------
     * 2) Avatar state machine:
     *    - avatar-thinking: model running but text idle
     *    - avatar-talking: text is actively growing
     *
     * CSS side (custom.css) drives the actual images:
     *   #message-input-container::before           -> talk_idle.png
     *   body.avatar-thinking #message-input...     -> thinking.gif
     *   body.avatar-talking  #message-input...     -> talk_loop.gif
     * ---------------------------------------------- */

    const body = document.body;

    let streaming = false;        // "Stop" button / spinner present
    let intervalId = null;        // polling for text growth
    let lastLen = 0;              // last length of assistant text
    let idleTicks = 0;            // how many polls with no growth

    const POLL_MS = 150;
    const IDLE_TICKS_FOR_THINKING = 3; // ~450ms of no growth = back to thinking

    // Once Chat.svelte starts calling the global hooks, we stop
    // changing the avatar from this heuristic watcher.
    let avatarManualControl = false;

    function applyThinking() {
        body.classList.add("avatar-thinking");
        body.classList.remove("avatar-talking");
    }

    function applyTalking() {
        body.classList.add("avatar-talking");
        body.classList.remove("avatar-thinking");
    }

    function applyIdle() {
        body.classList.remove("avatar-thinking");
        body.classList.remove("avatar-talking");
    }

    // Global APIs for Chat.svelte (and anything else) to call directly.
    function setThinking() {
        avatarManualControl = true;
        applyThinking();
    }

    function setTalking() {
        avatarManualControl = true;
        applyTalking();
    }

    function clearAvatarState() {
        avatarManualControl = true;
        applyIdle();
    }

    // Expose on window so the Svelte patch can call these
    window.setThinking = setThinking;
    window.setTalking = setTalking;
    window.clearAvatarState = clearAvatarState;

    // Also support CustomEvents emitted from Svelte (avatar:thinking/talking/idle)
    window.addEventListener("avatar:thinking", () => setThinking());
    window.addEventListener("avatar:talking", () => setTalking());
    window.addEventListener("avatar:idle", () => clearAvatarState());

    function getLatestAssistantText() {
        const assistants = document.querySelectorAll(".chat-assistant");
        if (!assistants.length) return "";

        const lastAssistant = assistants[assistants.length - 1];

        const content =
            lastAssistant.querySelector("#response-content-container") ||
            lastAssistant.querySelector('[id^="response-content-container"]');

        if (!content) return "";

        return (content.innerText || "").trim();
    }

    function stopPolling() {
        if (intervalId !== null) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    function startPolling() {
        stopPolling(); // just in case
        lastLen = 0;
        idleTicks = 0;
        applyThinking();

        intervalId = setInterval(() => {
            // If manual control has taken over, our heuristic stops.
            if (avatarManualControl) {
                stopPolling();
                return;
            }

            // Only care while streaming is actually true
            if (!streaming) {
                stopPolling();
                applyIdle();
                return;
            }

            const text = getLatestAssistantText();
            const len = text.length;

            if (len > lastLen) {
                // text is actively growing => talking
                applyTalking();
                idleTicks = 0;
            } else {
                // no growth
                idleTicks++;
                if (idleTicks >= IDLE_TICKS_FOR_THINKING && len > 0) {
                    // still has some text, but not changing => thinking
                    applyThinking();
                }
            }

            lastLen = len;
        }, POLL_MS);
    }

    function initStreamingWatcher() {
        // Streaming is active when the Stop button or spinner/skeleton
        // in the latest assistant is present. This is a fallback only,
        // and will auto-disable as soon as the global hooks are used.
        waitForSelector("#message-input-container")
            .then((container) => {
                const STOP_BUTTON_SELECTOR =
                    '#message-input-container button[aria-label="Stop"], ' +
                    '#message-input-container button[aria-label^="Stop "], ' +
                    '#message-input-container button.bg-white.rounded-full.p-1\\.5, ' +
                    '#message-input-container button:has(svg.animate-spin)';

                function getResponseContainer() {
                    const assistants = document.querySelectorAll(".chat-assistant");
                    if (!assistants.length) return null;
                    const lastAssistant = assistants[assistants.length - 1];
                    return (
                        lastAssistant.querySelector("#response-content-container") ||
                        lastAssistant.querySelector('[id^="response-content-container"]')
                    );
                }

                function hasSpinnerOrSkeleton() {
                    const content = getResponseContainer();
                    if (!content) return false;

                    const spinner =
                        content.querySelector("svg.animate-spin") ||
                        content.querySelector('svg[class*="animate-spin"]') ||
                        content.querySelector("path.spinner_") ||
                        content.querySelector("svg.spinner_");
                    if (spinner) return true;

                    // Treat an empty response container (skeleton) as thinking while streaming
                    const text = (content.innerText || "").trim();
                    if (text.length === 0 && content.children.length > 0) return true;

                    return false;
                }

                function hasStopButton() {
                    return !!container.querySelector(STOP_BUTTON_SELECTOR);
                }

                function updateStreamingFlag() {
                    // Once manual control is active, this fallback watcher
                    // will stop attempting to control the avatar.
                    if (avatarManualControl) {
                        streaming = false;
                        stopPolling();
                        return;
                    }

                    const nowStreaming = hasStopButton() || hasSpinnerOrSkeleton();

                    if (nowStreaming && !streaming) {
                        streaming = true;
                        lastLen = 0;
                        idleTicks = 0;
                        applyThinking(); // start in thinking state
                        startPolling();  // this will flip to talking when text grows
                        console.log(LOG_PREFIX, "streaming started (indicator present)");
                    } else if (!nowStreaming && streaming) {
                        // End streaming when indicators are gone.
                        streaming = false;
                        stopPolling();
                        applyIdle();
                        console.log(LOG_PREFIX, "streaming ended (no indicators)");
                    }
                }

                // Initial check in case a reply is already streaming on load
                updateStreamingFlag();

                // Watch the input container for send/stop swap
                const inputObserver = new MutationObserver(updateStreamingFlag);
                inputObserver.observe(container, { childList: true, subtree: true });

                // Watch the chat area for spinner/skeleton presence
                const chatRoot =
                    document.querySelector("#chat-container") || document.body;
                const chatObserver = new MutationObserver(updateStreamingFlag);
                chatObserver.observe(chatRoot, {
                    childList: true,
                    subtree: true,
                    characterData: true,
                });
            })
            .catch((err) => console.warn(LOG_PREFIX, err.message));
    }

    /* ------------------------------------------------
     * 3) Replace specific hero button image with t_spin
     * ---------------------------------------------- */
    function initHeroSpinImageSwap() {
        const CONTAINER_SELECTOR = "#C-EtZXGQhy";
        const IMG_SELECTOR =
            "#C-EtZXGQhy > div.h-full.flex.relative.max-w-full.flex-col > div > div > div > div.w-full.text-3xl.text-gray-800.dark\\:text-gray-100.text-center.flex.items-center.gap-4.font-primary > div > div.flex.flex-row.justify-center.gap-3.\\@sm\\:gap-3\\.5.w-fit.px-5.max-w-xl > div.flex.shrink-0.justify-center > div > div > button > img";
        const SPIN_SRC = "t_spin.gif";

        function applySwap(root) {
            const img = root.querySelector(IMG_SELECTOR);
            if (!img) return false;
            if (img.getAttribute("src") !== SPIN_SRC) {
                img.setAttribute("src", SPIN_SRC);
                img.removeAttribute("srcset");
            }
            return true;
        }

        waitForSelector(CONTAINER_SELECTOR)
            .then((container) => {
                applySwap(container);
                const observer = new MutationObserver(() => applySwap(container));
                observer.observe(container, { childList: true, subtree: true });
            })
            .catch((err) => console.warn(LOG_PREFIX, err.message));
    }

    /* ------------------------------------------------
     * Init
     * ---------------------------------------------- */

    document.addEventListener("DOMContentLoaded", () => {
        initSidebarTitleWatcher();
        initStreamingWatcher();      // fallback only; auto-disables when Chat.svelte takes over
        initHeroSpinImageSwap();
    });
})();
