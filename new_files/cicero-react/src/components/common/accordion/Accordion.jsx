import { useState, useContext } from "react";
import PropTypes from 'prop-types';
import minusIcon from "../../../assets/icons/minusIcon.svg";
import plusIcon from "../../../assets/icons/plusIcon.svg";
import ReavealAnimationProvider from "../revealAnimation/ReavealAnimationProvider";
import { LanguageContext } from "../../../contexts/LanguageContext";

const Accordion = ({ question }) => {
    const [isOpen, setIsOpen] = useState(false);
    const { isDark } = useContext(LanguageContext);

    const handleToggle = () => {
        setIsOpen(!isOpen);
    };

    return (
        <ReavealAnimationProvider topOrBottm={100}>
            <div
                className="w-full mx-auto rounded-[30px] flex items-center justify-center relative cursor-pointer"
                onClick={handleToggle}
            >
                <div
                    className={`absolute -inset-[2px] rounded-[30px] ${
                        isOpen 
                            ? "bg-gradient-to-t from-[var(--red-dark)] to-[var(--red-light)]"
                            : "bg-[var(--background)]"
                    }`}
                ></div>
                <div className="w-full h-full bg-[var(--surface-primary)] py-[40px] overflow-hidden pl-[30px] md:pl-[50px] pr-[30px] rounded-[30px] flex-col flex items-center justify-center z-10">
                    <button className="w-full font-['Inter'] text-start text-lg md:text-xl transition-all font-bold md:leading-[20px] uppercase flex items-center justify-between text-[var(--text-primary)]">
                        <span>{question.question}</span>
                        <span className="shrink-0">
                            <img
                                className={`${
                                    isOpen && "rotate-[180deg]"
                                } transition-all shrink-0 ${
                                    isDark ? 'brightness-0 invert' : 'brightness-0'
                                }`}
                                src={isOpen ? minusIcon : plusIcon}
                                alt="toggle"
                            />
                        </span>
                    </button>

                    <div
                        className={`content grid text-start transition-all overflow-hidden w-full font-['Inter'] text-base font-medium text-[var(--text-primary)] ${
                            isOpen
                                ? "grid-rows-[1fr] opacity-100 mt-[30px]"
                                : "grid-rows-[0fr] opacity-0"
                        }`}
                    >
                        <p className="overflow-hidden">{question.answer}</p>
                    </div>
                </div>
            </div>
        </ReavealAnimationProvider>
    );
};

Accordion.propTypes = {
    question: PropTypes.shape({
        question: PropTypes.string.isRequired,
        answer: PropTypes.string.isRequired
    }).isRequired
};

export default Accordion;
