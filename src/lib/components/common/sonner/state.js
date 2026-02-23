import { get } from 'svelte/store';
import { clientWritable } from './internal/helpers.js';
let toastsCounter = 0;
function createToastState() {
    const toasts = clientWritable([]);
    const heights = clientWritable([]);
    function addToast(data) {
        toasts.update((prev) => [data, ...prev]);
    }
    function create(data) {
        const { message, ...rest } = data;
        const id = typeof data?.id === 'number' || (data.id && data.id?.length > 0)
            ? data.id
            : toastsCounter++;
        const dismissable = data.dismissable === undefined ? true : data.dismissable;
        const type = data.type === undefined ? 'default' : data.type;
        const $toasts = get(toasts);
        const alreadyExists = $toasts.find((toast) => {
            return toast.id === id;
        });
        if (alreadyExists) {
            toasts.update((prev) => prev.map((toast) => {
                if (toast.id === id) {
                    return {
                        ...toast,
                        ...data,
                        id,
                        title: message,
                        dismissable,
                        type,
                        updated: true
                    };
                }
                return {
                    ...toast,
                    updated: false
                };
            }));
        }
        else {
            addToast({ ...rest, id, title: message, dismissable, type });
        }
        return id;
    }
    function dismiss(id) {
        if (id === undefined) {
            toasts.update((prev) => prev.map((toast) => ({ ...toast, dismiss: true })));
            return;
        }
        toasts.update((prev) => prev.map((toast) => (toast.id === id ? { ...toast, dismiss: true } : toast)));
        return id;
    }
    function remove(id) {
        if (id === undefined) {
            toasts.set([]);
            return;
        }
        toasts.update((prev) => prev.filter((toast) => toast.id !== id));
        return id;
    }
    function message(message, data) {
        return create({ ...data, type: 'default', message });
    }
    function error(message, data) {
        return create({ ...data, type: 'error', message });
    }
    function success(message, data) {
        return create({ ...data, type: 'success', message });
    }
    function info(message, data) {
        return create({ ...data, type: 'info', message });
    }
    function warning(message, data) {
        return create({ ...data, type: 'warning', message });
    }
    function loading(message, data) {
        return create({ ...data, type: 'loading', message });
    }
    function promise(promise, data) {
        if (!data) {
            // Nothing to show
            return;
        }
        let id = undefined;
        if (data.loading !== undefined) {
            id = create({
                ...data,
                promise,
                type: 'loading',
                message: data.loading
            });
        }
        const p = promise instanceof Promise ? promise : promise();
        let shouldDismiss = id !== undefined;
        p.then((response) => {
            // TODO: Clean up TS here, response has incorrect type
            // @ts-expect-error: Incorrect response type
            if (response && typeof response.ok === 'boolean' && !response.ok) {
                shouldDismiss = false;
                const message = typeof data.error === 'function'
                    ? // @ts-expect-error: Incorrect response type
                        data.error(`HTTP error! status: ${response.status}`)
                    : data.error;
                create({ id, type: 'error', message });
            }
            else if (data.success !== undefined) {
                shouldDismiss = false;
                const message = 
                // @ts-expect-error: TODO: Better function checking
                typeof data.success === 'function' ? data.success(response) : data.success;
                create({ id, type: 'success', message });
            }
        })
            .catch((error) => {
            if (data.error !== undefined) {
                shouldDismiss = false;
                const message = 
                // @ts-expect-error: TODO: Better function checking
                typeof data.error === 'function' ? data.error(error) : data.error;
                create({ id, type: 'error', message });
            }
        })
            .finally(() => {
            if (shouldDismiss) {
                // Toast is still in load state (and will be indefinitely — dismiss it)
                dismiss(id);
                id = undefined;
            }
            data.finally?.();
        });
        return id;
    }
    function custom(component, data) {
        const id = data?.id || toastsCounter++;
        create({ component, id, ...data });
        return id;
    }
    function removeHeight(id) {
        heights.update((prev) => prev.filter((height) => height.toastId !== id));
    }
    function setHeight(data) {
        const exists = get(heights).find((el) => el.toastId === data.toastId);
        if (exists === undefined) {
            heights.update((prev) => [data, ...prev]);
            return;
        }
        heights.update((prev) => prev.map((el) => {
            if (el.toastId === data.toastId) {
                return data;
            }
            else {
                return el;
            }
        }));
    }
    function reset() {
        toasts.set([]);
        heights.set([]);
    }
    return {
        // methods
        create,
        addToast,
        dismiss,
        remove,
        message,
        error,
        success,
        info,
        warning,
        loading,
        promise,
        custom,
        removeHeight,
        setHeight,
        reset,
        // stores
        toasts,
        heights
    };
}
export const toastState = createToastState();
// bind this to the toast function
function toastFunction(message, data) {
    return toastState.create({
        message,
        ...data
    });
}
const basicToast = toastFunction;
// We use `Object.assign` to maintain the correct types as we would lose them otherwise
export const toast = Object.assign(basicToast, {
    success: toastState.success,
    info: toastState.info,
    warning: toastState.warning,
    error: toastState.error,
    custom: toastState.custom,
    message: toastState.message,
    promise: toastState.promise,
    dismiss: toastState.dismiss,
    loading: toastState.loading
});
export const useEffect = (subscribe) => ({ subscribe });
