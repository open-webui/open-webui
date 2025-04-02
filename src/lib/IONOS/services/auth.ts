export const LOCALSTORAGE_SHOW_LOGIN_FORM = 'ionosgptShowLoginForm';

export const isShowLoginForm = (): boolean => {
	return JSON.parse(localStorage.getItem(LOCALSTORAGE_SHOW_LOGIN_FORM) ?? 'false');
}
