import { replaceOutsideCode } from './index';

export const citationMarkerRegex = /\s*(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/g;

export const removeCitationMarkersOutsideCode = (content: string) => {
	return replaceOutsideCode(content, (segment) => segment.replace(citationMarkerRegex, ''));
};
