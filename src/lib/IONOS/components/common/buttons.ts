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
		'all': 'border-2 outline-offset-4 rounded-3xl',
		'stateless': 'bg-blue-700 border-blue-700 text-white',
		'hover': 'hover:bg-blue-400 hover:border-blue-400 hover:text-white',
		'active': 'active:bg-blue-500 active:border-blue-500 active:text-white',
		'focus': 'focus:outline-blue-400',
		'pressed': 'bg-blue-700 border-blue-700 text-white',
		'disabled': 'bg-gray-450 border-gray-450 text-white cursor-default',
		'disabled-pressed': 'bg-blue-800 border-blue-800 text-white cursor-default',
	},
	'secondary': {
		'all': 'border-2 outline-offset-4',
		'stateless': 'bg-transparent border-blue-700 text-blue-700',
		'hover': 'hover:bg-blue-400 hover:border-blue-400 hover:text-white',
		'active': 'active:bg-blue-500 active:border-blue-500 active:text-white',
		'focus': 'focus:outline-blue-400',
		'pressed': 'bg-blue-700 border-blue-700 text-white',
		'disabled': 'bg-white border-gray-500 text-gray-500 cursor-default',
		'disabled-pressed': 'bg-blue-800 border-blue-800 text-white cursor-default',
	},
	'tertiary': {
		'all': 'border-2 border-transparent text-blue-700 outline-offset-4 rounded-3xl',
		'stateless': 'bg-transparent',
		'hover': 'hover:bg-blue-300 hover:bg-opacity-20',
		'active': 'active:bg-blue-300 active:bg-opacity-10',
		'focus': 'focus:outline-blue-400',
		'pressed': 'bg-transparent',
		'disabled': 'bg-transparent cursor-default text-blue-700',
		'disabled-pressed': 'bg-blue-100 cursor-default',
	},
	'caution': {
		'all': 'border-2 border-white text-red-500',
		'stateless': ' outline-offset-4',
		'hover': 'hover:bg-red-200 hover:bg-opacity-50',
		'active': 'active:bg-red-200 active:bg-opacity-65',
		'focus': 'focus:outline-blue-400',
		'pressed': 'bg-transparent',
		'disabled': 'bg-white cursor-default',
		'disabled-pressed': 'bg-red-100 cursor-default',
	},
	'special': {
		// bg-ai-main-500 hover:bg-ai-main-700
		'all': 'border-2 bg-purple-700 border-purple-700 text-white',
		'stateless': 'outline-offset-4',
		'hover': 'hover:bg-purple-600',
		'active': 'hover:bg-purple-600',
		'focus': 'focus:outline-purple-700',
		'pressed': 'bg-purple-600',
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
