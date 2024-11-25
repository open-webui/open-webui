/* eslint-disable react/prop-types */

import { forwardRef } from "react";

const WorkCard = ({ title, icon }, ref) => {
    return (
        <div
            ref={ref}
            className="w-full workCard mx-auto rounded-[30px] group/cardHover  flex items-center justify-center relative"
        >
            <div className="absolute -inset-[2px] bg-gradient-to-t from-black  to-primaryRed to-100% rounded-[30px]"></div>
            <div className="w-full h-full bg-bgDark py-[50px] px-5 rounded-[30px] flex-col flex items-center justify-center z-10">
                <div className="w-[100px] h-[100px] mx-auto rounded-full  flex items-center justify-center relative">
                    <div className="absolute -inset-[2px] bg-gradient-to-t from-[#CB1D1E]  to-[#F86A06] to-100% rounded-full"></div>
                    <div className="w-full h-full bg-black rounded-full flex items-center justify-center z-10">
                        <img
                            className="inset-0 m-auto group-hover/cardHover:scale-110 transition-all"
                            src={icon}
                            alt="draft icon"
                        />
                    </div>
                </div>
                <p className="text-xl text-center mt-5 uppercase font-SpaceGrotesk font-bold leading-[30px]">
                    {title}
                </p>
            </div>
        </div>
    );
};

export default forwardRef(WorkCard);
