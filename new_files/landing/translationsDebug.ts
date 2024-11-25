import { writable } from 'svelte/store';
import type { Writable } from 'svelte/store';

class TranslationsDebugger {
    private static instance: TranslationsDebugger;
    private debugEnabled: boolean = true;
    private initStartTime: number = 0;
    private events: Array<{ timestamp: number; event: string; details?: any }> = [];
    private translationStore: Writable<any>;

    private constructor() {
        this.translationStore = writable({
            currentLang: '',
            translations: {},
            isInitialized: false,
            lastError: null
        });
    }

    static getInstance(): TranslationsDebugger {
        if (!TranslationsDebugger.instance) {
            TranslationsDebugger.instance = new TranslationsDebugger();
        }
        return TranslationsDebugger.instance;
    }

    enableDebug(enabled: boolean = true) {
        this.debugEnabled = enabled;
    }

    startInit() {
        this.initStartTime = performance.now();
        this.logEvent('translations initialization started');
    }

    logEvent(event: string, details?: any) {
        if (!this.debugEnabled) return;

        const timestamp = performance.now();
        const timeFromInit = this.initStartTime ? (timestamp - this.initStartTime).toFixed(2) : 0;
        
        const logEntry = {
            timestamp,
            event,
            details,
            timeFromInit: `${timeFromInit}ms`
        };

        this.events.push(logEntry);
        console.log('[Translations Debug]', event, logEntry);
    }

    trackTranslation(key: string, result: string | null) {
        this.logEvent('translation requested', { 
            key, 
            result,
            success: result !== null && result !== key
        });
    }

    updateState(state: any) {
        this.translationStore.update(current => ({
            ...current,
            ...state
        }));
        this.logEvent('state updated', state);
    }

    getState() {
        let state;
        this.translationStore.subscribe(value => {
            state = value;
        })();
        return state;
    }

    getEvents() {
        return this.events;
    }

    printSummary() {
        if (!this.debugEnabled) return;

        console.group('Translations Debug Summary');
        console.log('Total events:', this.events.length);
        console.log('Init duration:', 
            this.events[this.events.length - 1]?.timestamp - this.initStartTime, 'ms');
        console.log('Current state:', this.getState());
        console.log('Events timeline:', this.events);
        console.groupEnd();
    }

    subscribe(callback: (value: any) => void) {
        return this.translationStore.subscribe(callback);
    }
}

export const translationsDebug = TranslationsDebugger.getInstance();
