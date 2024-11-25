import { createContext, useState, useEffect, useCallback, useContext } from 'react';
import { enTranslations } from '../translations/en';
import { ptTranslations } from '../translations/pt';

export const LanguageContext = createContext();

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (!context) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return {
        ...context,
        translations: context.language === 'pt' ? ptTranslations : enTranslations
    };
}

export function LanguageProvider({ children }) {
    const [language, setLanguage] = useState(() => {
        const savedLang = localStorage.getItem('language');
        if (savedLang) return savedLang;
        
        const userLang = navigator.language || navigator.userLanguage;
        return userLang.startsWith('pt') ? 'pt' : 'en';
    });

    useEffect(() => {
        localStorage.setItem('language', language);
        document.documentElement.lang = language;
    }, [language]);

    const toggleLanguage = useCallback(() => {
        setLanguage(prevLang => prevLang === 'en' ? 'pt' : 'en');
    }, []);

    const value = {
        language,
        setLanguage,
        toggleLanguage
    };

    return (
        <LanguageContext.Provider value={value}>
            {children}
        </LanguageContext.Provider>
    );
}
