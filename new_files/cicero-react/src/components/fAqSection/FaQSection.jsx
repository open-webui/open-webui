import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import { useLanguage } from "../../contexts/LanguageContext.jsx";
import Accordion from "../common/accordion/Accordion";
import ContainerWrapper from "../common/ContainerWrapper";

const FaQSection = () => {
    const headingRef = useRef(null);
    const sectionRef = useRef(null);
    const { translations } = useLanguage();

    useGSAP(() => {
        gsap.to(sectionRef.current, {
            yPercent: -100,
            opacity: 0,
            scrollTrigger: {
                trigger: sectionRef.current,
                scroller: "body",
                scrub: 1,
                start: "top 20%",
                end: "top -20%",
            },
        });

        gsap.from(headingRef.current, {
            scale: 0,
            opacity: 0,
            scrollTrigger: {
                trigger: ".faqSection",
                scroller: "body",
                scrub: true,
                end: "top 100%",
            },
        });
    }, []);

    const halfLength = Math.ceil(translations.faq.questions.length / 2);
    const firstColumn = translations.faq.questions.slice(0, halfLength);
    const secondColumn = translations.faq.questions.slice(halfLength);

    return (
        <section ref={sectionRef} className="faqSection py-16 bg-[var(--background)]">
            <ContainerWrapper>
                <div ref={headingRef}>
                    <h2 className="text-4xl md:text-5xl font-['Inter'] font-semibold text-center mb-16 text-[var(--foreground)]">
                        {translations.faq.title}
                    </h2>
                </div>

                <div className="mt-[50px]">
                    <div className="grid md:grid-cols-2 gap-8">
                        <div className="flex flex-col gap-5">
                            {firstColumn.map((question, index) => (
                                <Accordion key={index} question={question} />
                            ))}
                        </div>
                        <div className="flex flex-col gap-5">
                            {secondColumn.map((question, index) => (
                                <Accordion key={index + halfLength} question={question} />
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex justify-center mt-16">
                    <button className="try-it-now-btn bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300">
                        {translations.hero.cta}
                    </button>
                </div>
            </ContainerWrapper>
        </section>
    );
};

export default FaQSection;
