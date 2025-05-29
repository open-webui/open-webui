import { toast as sonnerToast } from 'svelte-sonner';
import { ariaMessage } from '$lib/stores';

class ToastService {
	announce(message) {
		ariaMessage.set('');
		setTimeout(() => {
			ariaMessage.set(message);
		}, 0);
	}

	success = (message) => {
		sonnerToast.success(message);
		this.announce(message);
	};
	error = (message) => {
		sonnerToast.error(message);
		this.announce(message);
	};
	info = (message) => {
		sonnerToast.info(message);
		this.announce(message);
	};

	warning = (message) => {
		sonnerToast.warning(message);
		this.announce(message);
	};
	custom = (content) => {
		sonnerToast.custom(content);
		const props = content?.componentProps;
		const title = props?.title;
		const body = props?.content;
		if (title || body) {
			this.announce([title, body].filter(Boolean).join(': '));
		}
	};
}

export const toast = new ToastService();
