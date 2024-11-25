import { useEffect, useState, useContext } from "react";
import { Link } from "react-router-dom";
import { FiSun, FiMoon } from 'react-icons/fi';

import linkedInIcon from "../../assets/icons/linkedin.svg";
import mediumIcon from "../../assets/icons/medium.svg";
import ContainerWrapper from "../common/ContainerWrapper";
import { LanguageContext } from "../../contexts/LanguageContext";

function Navbar() {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isDark, setIsDark] = useState(() => {
        const savedTheme = localStorage.getItem('theme');
        return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    const { language, toggleLanguage } = useContext(LanguageContext);

    useEffect(() => {
        const handleScroll = () => {
            if (window.scrollY > 50) {
                setIsScrolled(true);
            } else {
                setIsScrolled(false);
            }
        };

        window.addEventListener("scroll", handleScroll);

        return () => {
            window.removeEventListener("scroll", handleScroll);
        };
    }, []);

    useEffect(() => {
        if (isDark) {
            document.documentElement.classList.add('dark');
            document.documentElement.style.setProperty('--background', '#000000');
            document.documentElement.style.setProperty('--foreground', '#FFFFFF');
            document.documentElement.style.setProperty('--surface-primary', '#FFFFFF');
            document.documentElement.style.setProperty('--text-primary', '#000000');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.style.setProperty('--background', '#FFFFFF');
            document.documentElement.style.setProperty('--foreground', '#000000');
            document.documentElement.style.setProperty('--surface-primary', '#000000');
            document.documentElement.style.setProperty('--text-primary', '#FFFFFF');
        }
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }, [isDark]);

    const toggleTheme = () => setIsDark(!isDark);

    return (
        <div className="fixed w-full z-50">
            <ContainerWrapper>
                <nav
                    className={`flex items-center transition-all duration-500 justify-between py-2 ${
                        isScrolled ? "md:py-2" : "md:py-4"
                    }`}
                >
                    <Link
                        to="/"
                        className={`logo font-Inter hover:scale-110 transition-all px-6 py-2 rounded-md flex items-center justify-center mt-6
                                  bg-[var(--surface-primary)]`}
                    >
                        <h1 className="text-[var(--text-primary)] text-[2.7rem] font-bold tracking-tight">CICERO</h1>
                    </Link>

                    <div className="flex items-center gap-[30px]">
                        <div className="social flex items-center gap-5">
                            <Link 
                                to="https://blog.synthetic.lawyer" 
                                target="_blank"
                                className={`hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center
                                          bg-[var(--surface-primary)]`}
                            >
                                <img
                                    className={isDark ? 'brightness-0' : 'brightness-0 invert'}
                                    src={mediumIcon}
                                    height={16}
                                    width={16}
                                    alt="mediumIcon"
                                />
                            </Link>
                            <button
                                onClick={toggleLanguage}
                                className={`hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center text-xs
                                          bg-[var(--surface-primary)] text-[var(--text-primary)]`}
                                aria-label="Toggle language"
                                style={{ width: '32px', height: '32px' }}
                            >
                                {(language === 'en' ? 'PT' : 'EN')}
                            </button>
                            <button
                                onClick={toggleTheme}
                                className={`hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center
                                          bg-[var(--surface-primary)]`}
                                aria-label="Toggle theme"
                            >
                                {isDark ? (
                                    <FiSun className="w-4 h-4 text-[var(--text-primary)]" />
                                ) : (
                                    <FiMoon className="w-4 h-4 text-[var(--text-primary)]" />
                                )}
                            </button>
                            <Link 
                                to="https://www.linkedin.com/company/cicero-contracts" 
                                target="_blank"
                                className={`hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center
                                          bg-[var(--surface-primary)]`}
                            >
                                <img
                                    className={isDark ? 'brightness-0' : 'brightness-0 invert'}
                                    src={linkedInIcon}
                                    height={16}
                                    width={16}
                                    alt="linkedin"
                                />
                            </Link>
                        </div>
                    </div>
                </nav>
            </ContainerWrapper>
        </div>
    );
}

export default Navbar;
