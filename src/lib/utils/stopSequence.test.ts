import { describe, expect, it } from 'vitest';
import { decodeStopToken, getStopTokens } from './stopSequence';

describe('getStopTokens', () => {
        it('returns undefined for empty input', () => {
                expect(getStopTokens(null)).toBeUndefined();
                expect(getStopTokens(undefined)).toBeUndefined();
                expect(getStopTokens('')).toBeUndefined();
        });

        it('splits comma-separated sequences and drops empty tokens', () => {
                expect(getStopTokens('END, 100%, ,')).toEqual(['END', '100%']);
        });

        it('accepts array values', () => {
                expect(getStopTokens(['END', '100%'])).toEqual(['END', '100%']);
        });

        it('decodes backslash escapes', () => {
                expect(getStopTokens('\\n')).toEqual(['\n']);
                expect(decodeStopToken('END\\n')).toBe('END\n');
        });

        it('decodes valid percent-encoding', () => {
                expect(getStopTokens('%20')).toEqual([' ']);
        });

        it('keeps percent signs that are not part of a valid escape (#32648)', () => {
                expect(() => getStopTokens('100%')).not.toThrow();
                expect(getStopTokens('100%')).toEqual(['100%']);
                expect(getStopTokens('100%, 50%')).toEqual(['100%', '50%']);
        });

        it('keeps invalid escape sequences as-is', () => {
                expect(decodeStopToken('C:\\Users')).toBe('C:\\Users');
        });
});
