import { useContext } from "react";
import { LanguageContext } from "../../contexts/LanguageContext";
import { enTranslations } from "../../translations/en";
import { ptTranslations } from "../../translations/pt";
import ContainerWrapper from "../common/ContainerWrapper";

function WorkSection() {
    const { language } = useContext(LanguageContext);
    const translations = language === 'pt' ? ptTranslations : enTranslations;

    return (
        <section className="work-section py-16 md:py-24 bg-[var(--background)]">
            <ContainerWrapper>
                <h2 className="text-4xl md:text-5xl font-['Inter'] font-semibold text-center mb-16 text-[var(--foreground)]">
                    {translations.work.title}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 mb-16">
                    {translations.work.features.map((feature, index) => (
                        <div 
                            key={index} 
                            className="work-card p-8 rounded-lg bg-[var(--foreground)] border border-[var(--border-light)] hover:border-[var(--border-medium)] transition-all duration-300"
                        >
                            <h3 className="text-2xl font-['Inter'] font-semibold mb-4 text-[var(--background)]">
                                {feature.title}
                            </h3>
                            <p className="text-lg font-['Inter'] text-[var(--background)]">
                                {feature.description}
                            </p>
                        </div>
                    ))}
                </div>
                <div className="flex justify-center">
                    <button className="try-it-now-btn bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300">
                        {translations.hero.cta}
                    </button>
                </div>
            </ContainerWrapper>
        </section>
    );
}

export default WorkSection;
