import { useContext } from "react";
import { Link } from "react-router-dom";
import ContainerWrapper from "../common/ContainerWrapper";
import ReavealAnimationProvider from "../common/revealAnimation/ReavealAnimationProvider";
import { LanguageContext } from "../../contexts/LanguageContext";
import { enTranslations } from "../../translations/en";
import { ptTranslations } from "../../translations/pt";

const Footer = () => {
    const { language } = useContext(LanguageContext);
    const translations = language === 'pt' ? ptTranslations : enTranslations;

    return (
        <footer className="pt-[50px] pb-[30px] bg-[var(--background)]">
            <ContainerWrapper>
                <hr className="mb-[30px] h-[1px] w-full border-none bg-[var(--foreground)] opacity-20" />
                <ReavealAnimationProvider topOrBottm={100}>
                    <div className="flex flex-col">
                        <div className="flex flex-col md:flex-row items-start gap-[15px] md:gap-16">
                            <ul>
                                <li className="font-Inter hover:scale-105 transition-all mb-4 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="#">{translations.footer.aboutUs}</Link>
                                </li>
                                <li className="font-Inter hover:scale-105 transition-all mb-4 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="https://blog.synthetic.lawyer" target="_blank">{translations.footer.blog}</Link>
                                </li>
                                <li className="font-Inter hover:scale-105 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="#">{translations.footer.cookieSettings}</Link>
                                </li>
                            </ul>
                            <ul>
                                <li className="font-Inter hover:scale-105 transition-all mb-4 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="mailto:contact@cicero.chat">{translations.footer.contactUs}</Link>
                                </li>
                                <li className="font-Inter hover:scale-105 transition-all mb-4 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="https://www.linkedin.com/company/cicero-contracts" target="_blank">LinkedIn</Link>
                                </li>
                                <li className="font-Inter hover:scale-105 text-base font-semibold uppercase leading-[20px] text-[var(--foreground)]">
                                    <Link to="#">{translations.footer.termsPrivacy}</Link>
                                </li>
                            </ul>
                        </div>
                    </div>
                    <hr className="mt-[30px] h-[1px] w-full border-none bg-[var(--foreground)] opacity-20" />

                    <div className="flex flex-col md:flex-row items-center justify-between mt-[30px] w-full">
                        <div className="logo">
                            <h1 className="font-Inter font-bold text-[2.7rem] tracking-tight text-[var(--foreground)]">CICERO</h1>
                        </div>
                    </div>
                </ReavealAnimationProvider>
            </ContainerWrapper>
        </footer>
    );
};

export default Footer;
