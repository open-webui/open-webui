import { useLanguage } from "../../contexts/LanguageContext.jsx";
import ContainerWrapper from "../common/ContainerWrapper";
import ReavealAnimationProvider from "../common/revealAnimation/ReavealAnimationProvider";

const NewsLetter = () => {
    const { translations } = useLanguage();

    return (
        <section className="py-16 bg-[var(--background)]">
            <ContainerWrapper>
                <ReavealAnimationProvider topOrBottm={150}>
                    <div className="newsletter-container p-4 md:p-6 lg:p-[30px] rounded-[30px] max-w-2xl mx-auto bg-gradient-to-r from-[var(--red-light)] to-[var(--red-dark)]">
                        <h2 className="text-2xl md:text-3xl font-Inter font-semibold text-center mb-6 text-[var(--text-primary)]">
                            {translations.newsletter.title}
                        </h2>
                        <p className="text-center font-Inter text-base mb-8 max-w-md mx-auto text-[var(--text-primary)]">
                            {translations.newsletter.description}
                        </p>
                        <div className="w-full max-w-[400px] mx-auto bg-[var(--surface-primary)] rounded-lg md:rounded-full flex max-md:flex-col py-2 pr-2 max-md:pl-2">
                            <input
                                className="px-4 md:px-5 max-md:py-2 max-md:mb-2 font-Inter text-sm font-medium placeholder:text-[var(--text-secondary)] rounded-full text-[var(--text-primary)] w-full border-none outline-none bg-transparent"
                                type="email"
                                placeholder="Enter your email"
                            />
                            <button
                                className="bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white transition-all rounded-lg md:rounded-full px-6 py-2 font-Inter text-sm font-medium uppercase"
                                type="submit"
                            >
                                {translations.newsletter.button}
                            </button>
                        </div>
                    </div>
                </ReavealAnimationProvider>
            </ContainerWrapper>
        </section>
    );
};

export default NewsLetter;
