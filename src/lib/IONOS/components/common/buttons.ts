export enum ButtonType {
	primary = 'primary',
	secondary = 'secondary',
	tertiary = 'tertiary',
	caution = 'caution',
	special = 'special',
};

/* - Primary and Secondary refer to the mono types in Figma
 * - Officially there's also visited, which is omitted here
 * - "pressed" is not an official state, defined here like "active"
 * - "special" is not an official variant/type and product specific
 */
const stateMap = {
	'primary': {
		'all': 'border-2 outline-offset-4',
		'stateless': 'bg-blue-900 border-blue-900 text-white',
		'hover': 'hover:bg-blue-700 hover:border-blue-700 hover:text-white',
		'active': 'active:bg-blue-800 active:border-blue-800 active:text-white',
		'focus': 'focus:outline-blue-500',
		'pressed': 'bg-blue-800 border-blue-800 text-white',
		'disabled': 'bg-slate-500 border-slate-500 text-white cursor-default',
		'disabled-pressed': 'bg-blue-800 border-blue-800 text-white cursor-default',
	},
	'secondary': {
		'all': 'border-2 outline-offset-4',
		'stateless': 'bg-white border-blue-900 text-blue-900',
		'hover': 'hover:bg-blue-700 hover:border-blue-700 hover:text-white',
		'active': 'active:bg-blue-800 active:border-blue-800 active:text-white',
		'focus': 'focus:outline-blue-500',
		'pressed': 'bg-blue-800 border-blue-800 text-white',
		'disabled': 'bg-white border-slate-500 text-slate-500 cursor-default',
		'disabled-pressed': 'bg-blue-800 border-blue-800 text-white cursor-default',
	},
	'tertiary': {
		'all': 'border-2 border-transparent text-blue-900 outline-offset-4',
		'stateless': '',
		'hover': 'hover:bg-blue-200 hover:border-blue-200',
		'active': 'active:bg-blue-100 active:border-blue-100',
		'focus': 'focus:outline-blue-500',
		'pressed': 'bg-blue-100',
		'disabled': 'bg-white cursor-default',
		'disabled-pressed': 'bg-blue-100 cursor-default',
	},
	'caution': {
		'all': 'border-2 border-white',
		'stateless': 'text-red-700 outline-offset-4',
		'hover': 'hover:bg-red-200',
		'active': 'active:bg-red-300',
		'focus': 'focus:outline-sky-600',
		'pressed': 'bg-red-300',
		'disabled': 'bg-white text-red-700 cursor-default',
		'disabled-pressed': 'bg-red-300 cursor-default',
	},
	'special': {
		// bg-ai-main-500 hover:bg-ai-main-700
		'all': 'border-2 bg-ai-main-500 border-ai-main-500 text-white',
		'stateless': 'outline-offset-4',
		'hover': 'hover:bg-ai-main-700',
		'active': 'hover:bg-ai-main-700',
		'focus': 'focus:outline-ai-main-500',
		'pressed': 'bg-ai-main-700',
		'disabled': 'cursor-default',
		'disabled-pressed': 'cursor-default',
	},
};

export const stateClassBuilder = (type: ButtonType, disabled: boolean, pressed: boolean): string => {
	if (pressed && type == ButtonType.caution) {
		console.warn(`Button type ${type} with state pressed is not valid`);
	}

	return [
		stateMap[type]['all'] ?? '',
		!disabled && !pressed ? stateMap[type]['stateless'] : '',
		!disabled ? stateMap[type]['hover'] : '',
		!disabled && !pressed ? stateMap[type]['active'] : '',
		!disabled ? stateMap[type]['focus'] : '',
		disabled && !pressed ? stateMap[type]['disabled'] : '',
		pressed && !disabled ? stateMap[type]['pressed'] : '',
		pressed && disabled ? stateMap[type]['disabled-pressed'] : '',
	].join(' ');
}
