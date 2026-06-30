import translations from './translation.json';
import { describe, expect, test } from 'vitest';

describe('es-ES relative time labels', () => {
	test('use readable Spanish compact labels without underscore separators', () => {
		expect(translations['1m_time_ago']).toBe('hace 1 min');
		expect(translations['{{COUNT}}m_time_ago']).toBe('hace {{COUNT}} min');
		expect(translations['{{COUNT}}h_time_ago']).toBe('hace {{COUNT}} h');
		expect(translations['{{COUNT}}d_time_ago']).toBe('hace {{COUNT}} d');
		expect(translations['{{COUNT}}w_time_ago']).toBe('hace {{COUNT}} sem');
		expect(translations['{{COUNT}}y_time_ago']).toBe('hace {{COUNT}} a');
	});
});
