import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef, useContext, useEffect } from "react";
import { LanguageContext } from "../../contexts/LanguageContext";
import { enTranslations } from "../../translations/en";
import { ptTranslations } from "../../translations/pt";

function Hero() {
    const { language } = useContext(LanguageContext);
    const translations = language === 'pt' ? ptTranslations : enTranslations;
    const animatedText = useRef(null);
    const heroButtonRef = useRef(null);
    const heroTextRef = useRef(null);
    const timeline = useRef(null);

    // Handle scroll animation
    useGSAP(() => {
        gsap.to(".heroSection", {
            scrollTrigger: {
                trigger: ".heroSection",
                scroller: "body",
                pin: true,
                scrub: true,
            },
        });
    }, []);

    // Handle text animation
    useEffect(() => {
        if (timeline.current) {
            timeline.current.kill();
        }

        timeline.current = gsap.timeline();
        
        // Initial state with dot
        timeline.current.set(animatedText.current, { 
            innerHTML: `[ <span class="pulsating-dot"></span> ]`
        });
        
        // Wait for 4 seconds while dot pulsates
        timeline.current.to({}, { duration: 3 });
        
        // Text appears from left to right
        const finalText = translations.hero.subtitle + '.';
        const words = finalText.split(' ');
        const steps = words.length;
        
        for (let i = 0; i <= steps; i++) {
            const visibleWords = words.slice(0, i);
            const remainingSpace = " ".repeat(Math.max(1, 3));
            
            timeline.current.to(animatedText.current, {
                innerHTML: `[${remainingSpace}${visibleWords.join(' ')}${remainingSpace}]`,
                duration: 0.2,
                ease: "none"
            });
        }

        return () => {
            if (timeline.current) {
                timeline.current.kill();
            }
        };
    }, [language, translations.hero.subtitle]);

    // Combined text and button animation
    useEffect(() => {
        const tl = gsap.timeline({
            scrollTrigger: {
                trigger: ".heroSection",
                scroller: "body",
                scrub: 1,
                start: "top 0%",
                end: "top -100%",
            }
        });

        tl.to([heroTextRef.current, heroButtonRef.current], {
            y: "-490%",
            opacity: 0,
            duration: 1,
            ease: "power1.inOut",
        });
    }, []);

    return (
        <section className="heroSection w-full h-screen flex items-center justify-center relative bg-[var(--background)]">
            <div
                ref={heroTextRef}
                className="w-full max-w-[1440px] mx-auto text-center"
            >
                <div className="w-full text-5xl md:text-6xl lg:text-[80px] leading-tight lg:leading-[80px] font-Inter font-bold uppercase">
                    {translations.hero.title}
                </div>
                <div className="mt-2 text-[1.5rem] md:text-[1.875rem] font-Inter font-normal leading-[30px] bg-[#FFFF05]/70 inline-block px-4 py-2 rounded-lg">
                    <span ref={animatedText}></span>
                </div>
            </div>

            <button
                ref={heroButtonRef}
                className="try-it-now-btn absolute bottom-20 left-1/2 -translate-x-1/2 bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
            >
                {translations.hero.cta}
            </button>
        </section>
    );
}

export default Hero;
