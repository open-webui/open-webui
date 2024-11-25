// TRANSLATIONS CAVE WALL
import { writable, derived, get } from 'svelte/store';
import { translationsDebug } from './translationsDebug';
import { browser } from '$app/environment';
import type { i18n as i18nType } from 'i18next';

const TRANSLATIONS: Record<string, Record<string, string>> = {
    'en-US': {
        'hero.title': 'CONTRACTS IN THE FUTURE',
        'hero.subtitle': "It's time to simplify your contract drafting",
        'hero.cta': 'Try it now',
        'information.title': 'What We Do',
        'information.description': 'We help you draft, learn and fix contracts ',
        'information.descriptionBold': 'with AI',
        'work.title': 'HOW IT WORKS',
        'work.features.0.title': 'Not ChatGPT',
        'work.features.0.description': 'Our model was trained on millions (seriously!) of legal clauses',
        'work.features.1.title': 'Secure Document Management',
        'work.features.1.description': 'Enterprise-grade security for your sensitive legal documents',
        'work.features.2.title': 'Collaborative Editing',
        'work.features.2.description': 'Real-time collaboration tools for team contract review',
        'work.features.3.title': 'Automated Learning',
        'work.features.3.description': 'AI-driven insights and recommendations for contract optimization',
        'faq.title': 'FREQUENTLY ASKED QUESTIONS',
        'faq.q1': 'What is Cicero?',
        'faq.a1': 'Cicero is an AI-powered platform for drafting, learning, and fixing contracts.',
        'faq.q2': 'How does it work?',
        'faq.a2': 'Upload your contract or start from scratch, and our AI will help you draft, understand, and improve it.',
        'faq.q3': 'Is it secure?',
        'faq.a3': 'Yes, we use industry-standard encryption and security measures to protect your data.',
        'faq.q4': 'Who owns the copyright?',
        'faq.a4': 'You do.',
        'newsletter.title': 'Newsletter',
        'newsletter.description': 'Subscribe to our newsletter',
        'newsletter.button': 'Subscribe',
        'footer.aboutUs': 'About us',
        'footer.blog': 'Blog',
        'footer.contactUs': 'Contact us',
        'footer.termsPrivacy': 'Terms & privacy',
        'footer.cookieSettings': 'Cookie settings',
        'footer.rights': 'All rights reserved'
    },
    'pt-BR': {
        'hero.title': 'CONTRATOS NO FUTURO',
        'hero.subtitle': 'Chegou a hora de simplificar seus contratos',
        'hero.cta': 'Comece agora',
        'information.title': 'O Que Fazemos',
        'information.description': 'Usamos IA para ajudar você a criar, entender e aprimorar seus contratos ',
        'information.descriptionBold': 'com IA',
        'work.title': 'COMO FUNCIONA',
        'work.features.0.title': 'Muito além do ChatGPT',
        'work.features.0.description': 'Nossa IA foi treinada com milhões de cláusulas jurídicas reais',
        'work.features.1.title': 'Segurança Total',
        'work.features.1.description': 'Proteção de nível empresarial para seus documentos confidenciais',
        'work.features.2.title': 'Trabalho em Equipe',
        'work.features.2.description': 'Colabore em tempo real na revisão dos seus contratos',
        'work.features.3.title': 'Aprendizado Inteligente',
        'work.features.3.description': 'Sugestões personalizadas para melhorar seus contratos',
        'faq.title': 'DÚVIDAS FREQUENTES',
        'faq.q1': 'O que é o Cicero?',
        'faq.a1': 'O Cicero é uma plataforma que usa Inteligência Artificial para ajudar você a criar, entender e aprimorar seus contratos.',
        'faq.q2': 'Como funciona?',
        'faq.a2': 'É simples: envie seu contrato ou comece do zero. Nossa IA vai te ajudar a criar, entender e melhorar cada detalhe.',
        'faq.q3': 'É seguro?',
        'faq.a3': 'Com certeza! Utilizamos criptografia avançada e as melhores práticas de segurança do mercado para proteger seus dados.',
        'faq.q4': 'Quem é o dono dos direitos autorais?',
        'faq.a4': 'Você, sempre.',
        'newsletter.title': 'Fique por dentro',
        'newsletter.description': 'Receba nossas novidades e dicas exclusivas',
        'newsletter.button': 'Quero receber',
        'footer.aboutUs': 'Quem somos',
        'footer.blog': 'Blog',
        'footer.contactUs': 'Fale conosco',
        'footer.termsPrivacy': 'Termos e privacidade',
        'footer.cookieSettings': 'Preferências de cookies',
        'footer.rights': 'Todos os direitos reservados'
    }
};

// Initialize debugger
if (browser) {
    translationsDebug.startInit();
    translationsDebug.updateState({
        translations: TRANSLATIONS,
        isInitialized: false
    });
}

// CAVE LANGUAGE STORE
// Create a store for the current language
export const currentLang = writable(browser ? localStorage.getItem('preferredLanguage') || 'en-US' : 'en-US');

// Update debugger when language changes
currentLang.subscribe((lang) => {
    if (browser) {
        translationsDebug.updateState({ currentLang: lang });
    }
});

// Derived store for translations
export const t = derived(currentLang, (lang) => {
    return (key: string) => {
        const translation = TRANSLATIONS[lang]?.[key];
        if (!translation) {
            console.warn(`Missing translation for key: ${key} in language: ${lang}`);
            return key;
        }
        return translation;
    };
});

// Create a mock i18n object for landing page
export const createMockI18n = (): i18nType => {
    const currentLanguage = get(currentLang) || 'en-US';
    
    const mockI18n = {
        t: (key: string) => TRANSLATIONS[currentLanguage]?.[key] || key,
        isInitialized: true,
        language: currentLanguage,
        languages: ['en-US', 'pt-BR'],
        changeLanguage: () => Promise.resolve(mockI18n),
        on: () => mockI18n,
        off: () => mockI18n,
        reloadResources: () => Promise.resolve(),
        loadLanguages: () => Promise.resolve(),
        loadNamespaces: () => Promise.resolve(),
        hasResourceBundle: () => true,
        getResourceBundle: () => TRANSLATIONS,
        getResource: () => TRANSLATIONS[currentLanguage],
        addResourceBundle: () => mockI18n,
        addResource: () => mockI18n,
        getFixedT: () => ((key: string) => TRANSLATIONS[currentLanguage]?.[key] || key),
        init: () => Promise.resolve(mockI18n),
        loadResources: () => Promise.resolve(),
        use: () => mockI18n,
        store: {},
        services: { resourceStore: { data: TRANSLATIONS } },
        modules: { external: [] },
        options: {},
        dir: () => 'ltr',
        format: (value: string | number | boolean | null | undefined) => String(value),
        exists: (key: string) => !!TRANSLATIONS[currentLanguage]?.[key],
        setDefaultNamespace: () => mockI18n,
        hasLoadedNamespace: () => true,
        getDataByLanguage: () => TRANSLATIONS[currentLanguage],
        cloneInstance: () => mockI18n,
        resolvedLanguage: currentLanguage
    } as unknown as i18nType;
    
    return mockI18n;
};

// SWITCH CAVE WALL SIDE
export function toggleLanguage(): void {
    const current = browser ? localStorage.getItem('preferredLanguage') || 'en-US' : 'en-US';
    const newLang = current === 'en-US' ? 'pt-BR' : 'en-US';
    
    if (browser) {
        translationsDebug.logEvent('language toggle', {
            from: current,
            to: newLang
        });
    }
    
    if (browser) {
        localStorage.setItem('preferredLanguage', newLang);
    }
    currentLang.set(newLang);
    
    if (browser) {
        translationsDebug.updateState({ 
            isInitialized: true,
            lastError: null
        });
    }
}

// Print debug summary after a short delay to capture initial state
if (browser) {
    setTimeout(() => {
        translationsDebug.printSummary();
    }, 1000);
}
