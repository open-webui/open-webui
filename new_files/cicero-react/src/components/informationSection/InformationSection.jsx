/* eslint-disable react/prop-types */

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import ContainerWrapper from "../common/ContainerWrapper";
import Heading from "../common/Heading";

const InformationSection = ({
    title,
    description,
    descriptionBold,
    icon,
    image,
}) => {
    const infoTextRef = useRef(null);
    const infoImageRef = useRef(null);
    useGSAP(() => {
        gsap.fromTo(
            infoTextRef.current,
            { x: "-100%", opacity: 0 },
            {
                x: "0%",
                opacity: 1,
                scrollTrigger: {
                    trigger: infoTextRef.current,
                    scroller: "body",
                    scrub: true,
                    start: "top 75%",
                    end: "top 25%",
                },
                ease: "power1.inOut",
            }
        );
        gsap.fromTo(
            infoImageRef.current,
            { scale: 0, opacity: 0 },
            {
                scale: 1,
                opacity: 1,
                scrollTrigger: {
                    trigger: infoImageRef.current,
                    scroller: "body",
                    scrub: true,
                    start: "top 120%",
                    end: "top 50%",
                },
                ease: "power1.inOut",
            }
        );
    });

    return (
        <section className="infoSection mb-[50px]">
            <ContainerWrapper>
                <div className="grid md:grid-cols-2 items-center gap-5">
                    <div ref={infoTextRef} className="text-center py-2">
                        <div className="w-[100px] h-[100px] mx-auto rounded-full flex items-center justify-center relative">
                            <div className="absolute -inset-1 bg-gradient-to-t from-[#e5a4a5dc]  to-primaryRed to-100% rounded-full"></div>
                            <div className="w-full h-full bg-black rounded-full flex items-center justify-center z-10">
                                <img
                                    className="inset-0 m-auto"
                                    src={icon}
                                    alt="draft icon"
                                />
                            </div>
                        </div>

                        <Heading
                            title={title}
                            description={description}
                            descriptionBold={descriptionBold}
                        />
                        <button className="btn mt-[30px]">try it now</button>
                    </div>

                    <div
                        ref={infoImageRef}
                        className="p-12 border border-[#B10508]  rounded-[30px] bg-[rgba(255,255,255,0.10)]"
                    >
                        <img src={image} alt="image one" />
                    </div>
                </div>
            </ContainerWrapper>
        </section>
    );
};

export default InformationSection;
